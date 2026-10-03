// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef EXTENSIONS_HPP
#define EXTENSIONS_HPP

#include <map>
#include <string>

#include <common/cbasetypes.hpp>
#include <common/database.hpp>
#include <common/mmo.hpp>

/**
 * A server-side gate for behaviour that deviates from stock rAthena.
 *
 * Each extension is a named on/off switch with human-readable metadata.
 * The registry lives in db/extension_db.yml; a server operator or a mod
 * flips one on by shipping an override entry in db/import/extension_db.yml
 * (same mechanism as every other YAML database). Code paths that ride an
 * extension are wrapped in `if (extension_enabled("id")) { ... }` and are
 * inert until the flag is set, so a merged extension changes nothing by
 * default and can be turned on selectively per install.
 *
 * An extension can also declare typed values -- a number to tune, a string
 * to name something -- which an override sets by key. They are read with
 * extension_int() / extension_string(), which hand back the caller's stock
 * value while the extension is off.
 */
enum e_extension_value_type : uint8 {
	EXTVAL_INT = 0,
	EXTVAL_STRING,
};

struct s_extension_value {
	e_extension_value_type type;
	std::string description;
	int64 int_default;
	int64 int_value;
	int64 min;                  ///< Int only; a Value outside [min, max] is clamped.
	int64 max;
	std::string str_default;
	std::string str_value;
};

struct s_extension {
	std::string id;             ///< Stable identifier, e.g. "blaze_shield_drain".
	std::string name;           ///< Short human-readable label.
	std::string description;    ///< Multi-line explanation of what the flag changes.
	bool enabled;               ///< Current state after all imports have loaded.
	bool default_enabled;       ///< Value from db/extension_db.yml before any override.
	std::map<std::string, s_extension_value> values;  ///< By key, in display order.
};

class ExtensionDatabase : public TypesafeYamlDatabase<std::string, s_extension> {
public:
	ExtensionDatabase() : TypesafeYamlDatabase("EXTENSION_DB", 1) {}

	const std::string getDefaultLocation() override;
	uint64 parseBodyNode(const ryml::NodeRef& node) override;

private:
	bool parseValueNode(s_extension& ext, const ryml::NodeRef& node);
};

extern ExtensionDatabase extension_db;

/**
 * True if the named extension is registered and currently enabled.
 * An unknown identifier returns false -- a caller that misspells the
 * id gets stock behaviour rather than a crash, which matches how every
 * other optional gate in the server fails safe.
 */
bool extension_enabled(const std::string& id);

/**
 * The value of an Int key on an enabled extension, or `fallback` -- which
 * should be the stock number -- when the extension is off or unknown. A key
 * the extension does not declare as an Int is a programming error: it logs
 * once and returns `fallback`.
 */
int64 extension_int(const std::string& id, const std::string& key, int64 fallback);

/** As extension_int(), for a String key. */
std::string extension_string(const std::string& id, const std::string& key, const std::string& fallback);

/** The declared value, or nullptr. For tooling (@extensioninfo, scripts). */
const s_extension_value* extension_value(const std::string& id, const std::string& key);

void do_init_extensions();
void do_final_extensions();

#endif /* EXTENSIONS_HPP */
