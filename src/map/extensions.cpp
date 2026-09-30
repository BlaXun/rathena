// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#include "extensions.hpp"

#include <limits>
#include <set>

#include <common/core.hpp>  // db_path
#include <common/showmsg.hpp>
#include <common/utils.hpp>  // cap_value

ExtensionDatabase extension_db;

const std::string ExtensionDatabase::getDefaultLocation() {
	return std::string(db_path) + "/extension_db.yml";
}

/**
 * One entry of an extension's Values list. An entry with a Type declares the
 * key (Type, Default, Min, Max, Description); an entry with a Value sets it.
 * Both may appear together. Keys merge one at a time, so two mods that set
 * different keys on the same extension both take effect.
 * A bad entry is reported and skipped; the rest of the extension still loads.
 */
bool ExtensionDatabase::parseValueNode(s_extension& ext, const ryml::NodeRef& node) {
	std::string key;

	if (!this->asString(node, "Key", key))
		return false;

	auto it = ext.values.find(key);

	if (this->nodeExists(node, "Type")) {
		std::string type_name;

		if (!this->asString(node, "Type", type_name))
			return false;

		s_extension_value value = {};

		if (type_name == "Int") {
			value.type = EXTVAL_INT;
			value.min = std::numeric_limits<int64>::min();
			value.max = std::numeric_limits<int64>::max();

			if (this->nodeExists(node, "Min") && !this->asInt64(node, "Min", value.min))
				return false;
			if (this->nodeExists(node, "Max") && !this->asInt64(node, "Max", value.max))
				return false;
			if (value.min > value.max) {
				this->invalidWarning(node, "Extension %s value %s has Min above Max, skipping.\n", ext.id.c_str(), key.c_str());
				return false;
			}
			if (this->nodeExists(node, "Default") && !this->asInt64(node, "Default", value.int_default))
				return false;
			value.int_default = cap_value(value.int_default, value.min, value.max);
			value.int_value = value.int_default;
		} else if (type_name == "String") {
			value.type = EXTVAL_STRING;

			if (this->nodeExists(node, "Default") && !this->asString(node, "Default", value.str_default))
				return false;
			value.str_value = value.str_default;
		} else {
			this->invalidWarning(node["Type"], "Extension %s value %s has unknown Type \"%s\" (Int or String), skipping.\n", ext.id.c_str(), key.c_str(), type_name.c_str());
			return false;
		}

		if (this->nodeExists(node, "Description") && !this->asString(node, "Description", value.description))
			return false;

		it = ext.values.insert_or_assign(key, value).first;
	} else if (it == ext.values.end()) {
		this->invalidWarning(node, "Extension %s has no value %s. A value is declared with a Type before anything can set it, skipping.\n", ext.id.c_str(), key.c_str());
		return false;
	}

	if (!this->nodeExists(node, "Value"))
		return true;

	s_extension_value& value = it->second;

	if (value.type == EXTVAL_INT) {
		int64 set;

		if (!this->asInt64(node, "Value", set))
			return false;
		if (set < value.min || set > value.max) {
			this->invalidWarning(node["Value"], "Extension %s value %s must be between %" PRId64 " and %" PRId64 ", capping.\n", ext.id.c_str(), key.c_str(), value.min, value.max);
			set = cap_value(set, value.min, value.max);
		}
		value.int_value = set;
	} else {
		if (!this->asString(node, "Value", value.str_value))
			return false;
	}

	return true;
}

uint64 ExtensionDatabase::parseBodyNode(const ryml::NodeRef& node) {
	std::string id;

	if (!this->asString(node, "Id", id))
		return 0;

	std::shared_ptr<s_extension> ext = this->find(id);
	bool exists = ext != nullptr;

	if (!exists) {
		// A brand-new entry (as opposed to an override) needs a Name so it
		// has something to show under @extensions. Description and Enabled
		// have sensible defaults.
		if (!this->nodesExist(node, {"Name"}))
			return 0;

		ext = std::make_shared<s_extension>();
		ext->id = id;
		ext->enabled = false;
		ext->default_enabled = false;
	}

	if (this->nodeExists(node, "Name")) {
		std::string name;

		if (!this->asString(node, "Name", name))
			return 0;

		ext->name = name;
	}

	if (this->nodeExists(node, "Description")) {
		std::string description;

		if (!this->asString(node, "Description", description))
			return 0;

		ext->description = description;
	}

	if (this->nodeExists(node, "Enabled")) {
		bool enabled = false;

		if (!this->asBool(node, "Enabled", enabled))
			return 0;

		ext->enabled = enabled;

		// The first sighting of an extension records its default. An
		// import that flips 'Enabled' later moves 'enabled' but leaves
		// 'default_enabled' alone, so tooling can tell "on because the
		// stock db says so" apart from "on because a mod turned it on".
		if (!exists)
			ext->default_enabled = enabled;
	}

	if (this->nodeExists(node, "Values")) {
		const auto& valuesNode = node["Values"];

		if (!valuesNode.is_seq()) {
			this->invalidWarning(valuesNode, "Extension %s Values should be a sequence of entries with a Key.\n", id.c_str());
		} else {
			for (const auto& valueNode : valuesNode)
				this->parseValueNode(*ext, valueNode);
		}
	}

	if (!exists)
		this->put(id, ext);

	return 1;
}

bool extension_enabled(const std::string& id) {
	std::shared_ptr<s_extension> ext = extension_db.find(id);

	return ext != nullptr && ext->enabled;
}

const s_extension_value* extension_value(const std::string& id, const std::string& key) {
	std::shared_ptr<s_extension> ext = extension_db.find(id);

	if (ext == nullptr)
		return nullptr;

	auto it = ext->values.find(key);

	return it == ext->values.end() ? nullptr : &it->second;
}

// The typed read behind extension_int / extension_string: the value when the
// extension is on and declares `key` with this type, otherwise nullptr. A
// missing or mistyped key is the caller's bug, so it is reported -- once per
// key, since these are read on hot paths.
static const s_extension_value* extension_read(const std::string& id, const std::string& key, e_extension_value_type type) {
	if (!extension_enabled(id))
		return nullptr;

	const s_extension_value* value = extension_value(id, key);

	if (value != nullptr && value->type == type)
		return value;

	static std::set<std::string> reported;

	if (reported.insert(id + "/" + key).second)
		ShowWarning("extension %s has no %s value \"%s\"; using the stock value.\n", id.c_str(), type == EXTVAL_INT ? "Int" : "String", key.c_str());

	return nullptr;
}

int64 extension_int(const std::string& id, const std::string& key, int64 fallback) {
	const s_extension_value* value = extension_read(id, key, EXTVAL_INT);

	return value != nullptr ? value->int_value : fallback;
}

std::string extension_string(const std::string& id, const std::string& key, const std::string& fallback) {
	const s_extension_value* value = extension_read(id, key, EXTVAL_STRING);

	return value != nullptr ? value->str_value : fallback;
}

void do_init_extensions() {
	extension_db.load();
}

void do_final_extensions() {
	extension_db.clear();
}
