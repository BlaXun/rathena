// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef EXTENSIONS_HPP
#define EXTENSIONS_HPP

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
 */
struct s_extension {
	std::string id;             ///< Stable identifier, e.g. "blaze_shield_drain".
	std::string name;           ///< Short human-readable label.
	std::string description;    ///< Multi-line explanation of what the flag changes.
	bool enabled;               ///< Current state after all imports have loaded.
	bool default_enabled;       ///< Value from db/extension_db.yml before any override.
};

class ExtensionDatabase : public TypesafeYamlDatabase<std::string, s_extension> {
public:
	ExtensionDatabase() : TypesafeYamlDatabase("EXTENSION_DB", 1) {}

	const std::string getDefaultLocation() override;
	uint64 parseBodyNode(const ryml::NodeRef& node) override;
};

extern ExtensionDatabase extension_db;

/**
 * True if the named extension is registered and currently enabled.
 * An unknown identifier returns false -- a caller that misspells the
 * id gets stock behaviour rather than a crash, which matches how every
 * other optional gate in the server fails safe.
 */
bool extension_enabled(const std::string& id);

void do_init_extensions();
void do_final_extensions();

#endif /* EXTENSIONS_HPP */
