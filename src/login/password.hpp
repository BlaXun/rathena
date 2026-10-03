// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#ifndef PASSWORD_HPP
#define PASSWORD_HPP

#include <string>

#include <common/cbasetypes.hpp>

/**
 * Stored account passwords, as salted one-way hashes.
 *
 * rAthena stores `login.user_pass` as plain text (or unsalted MD5), so anyone
 * with the database -- or a copy of it -- can read every password, and people
 * reuse passwords. This stores PBKDF2-HMAC-SHA256 instead:
 *
 *   $pbkdf2-sha256$<iterations>$<salt, base64>$<hash, base64>
 *
 * A hash cannot be turned back into the password; it can only be guessed at,
 * one slow guess at a time. The iteration count is part of the string, so it
 * can be raised later without breaking the hashes already stored.
 *
 * Plain-text passwords still verify, and are hashed the next time the account
 * is saved -- which a successful login always does -- so existing accounts
 * migrate without anyone doing anything.
 */
namespace password {

/// Flags recorded beside a hash, so a check that needs the plain text (is this
/// a weak password? the default one?) still works after it is gone.
enum e_password_flag : uint8 {
	PASSWORD_WEAK = 0x01,     ///< not 8-23 printable characters, blank, or the account name
	PASSWORD_DEFAULT = 0x02,  ///< exactly "ragnarok", the app's first-run default
};

/// True if `stored` is one of our hashes rather than a plain-text password.
bool is_hashed(const char* stored);

/// Hash a plain-text password with a fresh random salt.
std::string hash(const std::string& plain);

/// Check a plain-text password against a stored hash.
bool verify(const std::string& plain, const char* stored);

/// The PASSWORD_* flags for a plain-text password on account `userid`.
uint8 flags(const std::string& plain, const std::string& userid);

} // namespace password

#endif /* PASSWORD_HPP */
