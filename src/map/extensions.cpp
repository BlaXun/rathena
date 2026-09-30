// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#include "extensions.hpp"

#include <common/core.hpp>  // db_path
#include <common/showmsg.hpp>

ExtensionDatabase extension_db;

const std::string ExtensionDatabase::getDefaultLocation() {
	return std::string(db_path) + "/extension_db.yml";
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

	if (!exists)
		this->put(id, ext);

	return 1;
}

bool extension_enabled(const std::string& id) {
	std::shared_ptr<s_extension> ext = extension_db.find(id);

	return ext != nullptr && ext->enabled;
}

void do_init_extensions() {
	extension_db.load();
}

void do_final_extensions() {
	extension_db.clear();
}
