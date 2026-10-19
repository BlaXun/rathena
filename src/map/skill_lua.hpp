// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef SKILL_LUA_HPP
#define SKILL_LUA_HPP

#include <memory>
#include <vector>

#include <common/cbasetypes.hpp>
#include <common/mmo.hpp>

/**
 * Skill, item and player hooks written in Lua.
 *
 * Every hook, and what it decides (each is described below):
 *
 *   skill(name, {...})   ratio      the skill's damage ratio
 *                        hit        its accuracy
 *                        element    its element
 *                        on_hit     actions after each hit (drain, heal, status, ...)
 *                        on_steal   which drop TF_STEAL takes
 *                        level      the base level its formula reads for a player
 *                        job_level  the job level its formula reads for a player
 *                        heal       what AL_HEAL, AB_HIGHNESSHEAL or AB_CHEAL restores
 *   item(aegis, {...})   on_attack     the wearer attacked
 *                        on_hit_taken  the wearer was attacked
 *   player({...})        base_stat  what a player's base stat counts for
 *                        cast_dex   the DEX the cast-time and skill-delay formulas read
 *
 * A hook is off until a mod registers it; with none registered the server
 * behaves as stock rAthena. Server extensions, the other way a mod switches
 * behaviour on, are in doc/extensions.md.
 *
 * The files listed in db/import/lua/load.txt (or, with no list, every .lua
 * file in db/import/lua) are run once at start-up, in a sandbox, and
 * register hooks by skill name:
 *
 *   skill("MG_FIREBOLT", {
 *     priority = 3,                           -- 0..10, lower runs first; 5 is the default
 *     ratio   = function(c, stock) return stock + c.caster.int // 2 end,
 *     hit     = function(c, stock) ... end,   -- accuracy
 *     element = function(c, stock) ... end,   -- an ELE_* constant
 *     on_hit  = function(c) ... end,          -- after each hit is calculated
 *   })
 *
 * ratio, hit and element run on top of the skill's own class (src/map/skills),
 * so they reach every skill that has one; the stock result is passed in and
 * returning nil keeps it. on_hit runs from skill_attack for any skill, and
 * may ask for a few actions (drain, heal, status, polymorph), which are
 * applied once the hit has been dealt. Nothing a script does can reach the
 * disk, the network or the server's memory; an error or a runaway loop
 * switches that one hook off and says so in the log.
 *
 * One more skill hook, only meaningful on TF_STEAL:
 *
 *   skill("TF_STEAL", {
 *     on_steal = function(c)
 *       for _, drop in ipairs(c.drops) do
 *         if drop.is_card and c:chance(drop.rate) then
 *           return drop                       -- give this drop
 *         end
 *       end
 *       return nil                            -- fall through to stock
 *     end,
 *   })
 *
 * on_steal runs from pc_steal_item after the DEX/level success check, with
 * c.drops holding the mob's stealable drops ({nameid, rate, is_card,
 * is_equip, is_etc, type}). The hook may return one of those entries (or any
 * table with a matching `nameid`, or the nameid as an integer) to force that
 * drop; returning nil lets the stock slot-order loop run as if no hook
 * existed. First non-nil return in the priority chain wins.
 *
 * Two more hooks decide which level a skill's formula reads:
 *
 *   skill("SR_GATEOFHELL", {
 *     level     = function(c, stock) return math.min(stock, 99) end,
 *     job_level = function(c, stock) return 70 end,
 *   })
 *
 * They run wherever a formula reads a player's base or job level for that
 * skill's output, also for skills with no class of their own. level:
 * RK_DRAGONBREATH, RK_DRAGONBREATH_WATER, RK_ENCHANTBLADE,
 * NC_SELFDESTRUCTION, SR_GATEOFHELL, SR_CRESCENTELBOW, AB_RENOVATIO,
 * LG_EXEEDBREAK, OB_ZANGETSU, KO_JYUMONJIKIRI, SJ_GRAVITYCONTROL, the
 * Elemental Master's EM_EL_ skills (the master's level), and in pre-renewal
 * AL_HEAL, AB_HIGHNESSHEAL, PR_TURNUNDEAD; AL_DEMONBANE, SL_SMA,
 * TK_JUMPKICK, SG_SUN_ANGER, SG_MOON_ANGER, SG_STAR_ANGER. job_level:
 * RL_QD_SHOT, LG_EXEEDBREAK, MI_RUSH_WINDMILL, WA_MOONLIT_SERENADE.
 * `stock` is the real level. c.caster is the player; there is
 * no c.target and c.skill_lv is 0, so a hook that reads c.target fails and is
 * switched off. The result is kept between 0 and the server's level limit.
 * Monsters' levels are never asked about.
 *
 * And one decides what a heal skill restores:
 *
 *   skill("AB_CHEAL", {
 *     heal = function(c, stock) return c.base * 85 // 100 end,
 *   })
 *
 * heal runs for AL_HEAL, AB_HIGHNESSHEAL and AB_CHEAL when they heal (not
 * when Heal damages an Undead). `stock` is the amount the server would
 * restore; c.base is that amount before the skill's own bonus, which only
 * AB_CHEAL has (2.5 % per party member). c.target is the unit being healed.
 *
 * For a player, c.caster and c.target also carry base_str, base_agi,
 * base_vit, base_int, base_dex and base_luk: the stats as the player raised
 * them, where str, agi and the rest are the totals in use (with job, gear
 * and status bonuses). A hook can so reward what was invested in a stat:
 *
 *   heal = function(c, stock)
 *     return stock * (100 + math.max(0, c.caster.base_int - 99)) // 100
 *   end
 *
 * Player hooks are not tied to a skill or an item; they run for every player:
 *
 *   player({
 *     priority  = 5,
 *     base_stat = function(c, stock)          -- c.stat: "str", "agi", ... "luk"
 *       if stock <= 99 then return stock end
 *       return 99 + (stock - 99) // 3         -- above 99 a point counts for a third
 *     end,
 *     cast_dex  = function(c, stock)          -- stock: the DEX in use, bonuses included
 *       return stock
 *     end,
 *   })
 *
 * base_stat decides what a stat as the player raised it (c.caster.base_str
 * and so on, `stock` here) counts for wherever the server uses it: the
 * status calculation, the status window's bonus column, the weight limit,
 * Marionette Control, Beast Bane with the Hunter spirit, and the Vacuum
 * Extreme and Bind Trap resistances. Job, equipment and status bonuses are
 * added on top afterwards; allocation, resets and saving keep the raised
 * value. cast_dex decides the DEX the cast-time formula reads for a player
 * (pre-renewal's cast time; renewal's variable cast time, beside INT), and the
 * skill-delay one with delay_dependon_dex. Both run while the
 * player's status is being worked out, so c.caster carries only id, name,
 * job, level, job_level and base_str .. base_luk -- no totals, no HP or SP --
 * and there is no c.target. The results are kept between 0 and 65535.
 *
 * Two mods may hook the same part of the same skill: every registered hook
 * runs, in ascending priority order (ties broken by mod load order). For
 * ratio, hit and element each hook sees what the previous one returned as
 * `stock`, so the chain composes. For on_hit each hook queues its own
 * actions (drain, heal, status, polymorph) and they are applied together
 * once the hit is dealt. A mod that redeclares a hook replaces its own
 * previous registration -- a mod never fights itself.
 *
 * Equipped items can also run hooks, through a separate registration keyed
 * by item AegisName:
 *
 *   item("VORPAL_BLADE", {
 *     priority = 5,                          -- same 0..10 chain as skill()
 *     on_attack = function(c)                -- the wearer swung at something
 *       if c.connected and c.critical then c:heal(50, 0) end
 *     end,
 *     on_hit_taken = function(c) ... end,    -- something swung at the wearer
 *   })
 *
 * on_attack fires for every attack by any unit that has the item equipped
 * (a card counts when it is slotted in something equipped)
 * -- normal attacks and skill attacks, hits and misses -- after the damage
 * calculation is finalized. on_hit_taken fires the same way, but keyed on
 * the defender's equipment. In both hooks `c` carries the full outcome:
 * `c.connected` (did damage apply), `c.critical`, `c.damage`, `c.element`,
 * `c.skill_id` (0 for a normal attack), plus the usual `c.caster` and
 * `c.target` -- which also now expose each equip slot's item id, so a hook
 * can gate on gear without re-registering.
 *
 * Besides drain, heal, status and polymorph, any hook may ask for
 * c:cast(skill, level, who): a skill cast the way bAutoSpell casts one, at
 * "target" (default) or "caster". No Lua hook runs during that cast, so an
 * item that casts a bolt on every hit cannot trigger itself in a loop. A
 * ground skill's later hits (Storm Gust's ticks) are not part of the cast
 * and do run hooks: an on_attack that casts one should check c.skill_id.
 *
 * item() hooks chain the same way skill() hooks do: multiple mods can
 * register for the same item, and each runs in priority order, queuing
 * actions into the same pending hit. A unit without the item equipped --
 * mobs, homunculi, players who took it off -- does not fire the hook.
 */

struct block_list;

enum e_skill_lua_action : uint8 {
	SKILL_LUA_DRAIN = 0,
	SKILL_LUA_HEAL,
	SKILL_LUA_STATUS,
	SKILL_LUA_POLYMORPH,
	SKILL_LUA_CAST,
};

/// One thing an on_hit hook asked for. Units are kept by id, never by
/// pointer: by the time it is applied, the target may have died.
struct s_skill_lua_action {
	e_skill_lua_action kind;
	int32 unit_id;      ///< who it happens to
	int32 type;         ///< SKILL_LUA_STATUS: the sc_type; SKILL_LUA_CAST: the skill id
	int32 rate;         ///< SKILL_LUA_STATUS: chance out of 10000
	int32 val1;         ///< SKILL_LUA_STATUS; SKILL_LUA_CAST: the skill level
	int64 duration;     ///< SKILL_LUA_STATUS, in milliseconds
	int64 hp, sp;       ///< SKILL_LUA_HEAL
};

struct s_skill_lua_hit {
	int32 src_id;
	int32 target_id;
	uint16 skill_id;
	int64 damage;
	int32 race;         ///< the target's, when the hit was calculated
	int32 class_;
	std::vector<s_skill_lua_action> actions;
};

void do_init_skill_lua();
void do_final_skill_lua();

/// Put the Lua wrapper on the skills that have hooks. Called whenever the
/// skill database has (re)built its skill classes.
void skill_lua_attach();

/// Fire every hook interested in this attack:
///  - a skill()'s on_hit, if skill_id is set and the skill is hooked;
///  - item()'s on_attack, for each item equipped on `src`;
///  - item()'s on_hit_taken, for each item equipped on `target`.
/// Each hook may queue drain/heal/status/polymorph actions; they are
/// returned together rather than applied here, so they happen after the
/// hit is dealt. Returns nullptr when no action was queued.
///
/// `dmg_lv` is the attack's connection result (ATK_DEF means it landed),
/// `critical` is true for a critical, `element` is the final attack element
/// (ELE_*), and `attack_type` carries the usual BF_WEAPON/BF_MAGIC/BF_MISC
/// mask. skill_id is 0 for a normal weapon attack.
std::unique_ptr<s_skill_lua_hit> skill_lua_on_damage(block_list* src, block_list* target, uint16 skill_id, uint16 skill_lv, int64 damage, int32 attack_type, int32 dmg_lv, bool critical, int32 element);

/// Apply what the hooks asked for. Does nothing for an empty hit.
void skill_lua_apply(std::unique_ptr<s_skill_lua_hit>& hit);

/// Give TF_STEAL's on_steal hook a chance to pick which stealable drop the
/// thief gets. Returns the chosen drop's nameid, or 0 to let the stock
/// slot-order loop in pc_steal_item run as normal. Caller must still check
/// that the returned nameid names a stealable entry on the mob.
t_itemid skill_lua_on_steal(struct block_list* src, struct block_list* target, uint16 skill_lv);

/// The base level a skill's formula should read for `bl`: `stock` unless a
/// mod's level hook on that skill says otherwise. Always `stock` when no hook
/// is registered.
int32 skill_lua_level(uint16 skill_id, const block_list* bl, int32 stock);

/// The player() hooks: the value a base stat counts for (`stat` is "str",
/// "agi", "vit", "int", "dex" or "luk"), and the DEX the cast-time and
/// skill-delay formulas read. Both return `stock` when no hook is registered.
class map_session_data;
int32 skill_lua_base_stat(const map_session_data& sd, const char* stat, int32 stock);
int32 skill_lua_cast_dex(const map_session_data& sd, int32 stock);

/// As skill_lua_level(), for the job level and the job_level hook.
int32 skill_lua_job_level(uint16 skill_id, const block_list* bl, int32 stock);

/// The amount a heal skill restores: `stock` unless a mod's heal hook on that
/// skill says otherwise. `base` is the amount before the skill's own bonus
/// (Coluceo Heal's bonus per party member); the hook reads it as c.base.
int32 skill_lua_heal(uint16 skill_id, uint16 skill_lv, const block_list* src, const block_list* target, int32 stock, int32 base);

#endif /* SKILL_LUA_HPP */
