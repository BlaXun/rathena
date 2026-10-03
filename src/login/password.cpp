// Copyright (c) rAthena Dev Teams - Licensed under GNU GPL
// For more information, see LICENCE in the main folder

#include "password.hpp"

#include <array>
#include <cctype>
#include <cstring>
#include <random>
#include <vector>

namespace {

// ---------------------------------------------------------------------------
// SHA-256 (FIPS 180-4). Written out here rather than linking a crypto library:
// the login server has no other use for one.
// ---------------------------------------------------------------------------

constexpr uint32 K[64] = {
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
};

using State = std::array<uint32, 8>;
using Digest = std::array<uint8, 32>;

constexpr State INITIAL = { 0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19 };

inline uint32 rotr(uint32 x, int n) { return (x >> n) | (x << (32 - n)); }

void compress(State& h, const uint8* block) {
	uint32 w[64];
	for (int i = 0; i < 16; i++)
		w[i] = (uint32)block[i * 4] << 24 | (uint32)block[i * 4 + 1] << 16 | (uint32)block[i * 4 + 2] << 8 | block[i * 4 + 3];
	for (int i = 16; i < 64; i++) {
		uint32 s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
		uint32 s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
		w[i] = w[i - 16] + s0 + w[i - 7] + s1;
	}
	uint32 a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
	for (int i = 0; i < 64; i++) {
		uint32 t1 = hh + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i];
		uint32 t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
		hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
	}
	h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
}

/// Finish a hash whose state already covers `prefix_len` bytes (a whole number
/// of 64-byte blocks), with `data` as the rest of the message.
Digest finish(State h, uint64 prefix_len, const uint8* data, size_t len) {
	uint64 total = prefix_len + len;
	while (len >= 64) {
		compress(h, data);
		data += 64;
		len -= 64;
	}
	uint8 block[128] = {};
	std::memcpy(block, data, len);
	block[len] = 0x80;
	size_t blocks = len + 9 > 64 ? 2 : 1;
	uint64 bits = total * 8;
	for (int i = 0; i < 8; i++)
		block[blocks * 64 - 1 - i] = (uint8)(bits >> (8 * i));
	for (size_t i = 0; i < blocks; i++)
		compress(h, block + i * 64);
	Digest out;
	for (int i = 0; i < 8; i++) {
		out[i * 4] = (uint8)(h[i] >> 24);
		out[i * 4 + 1] = (uint8)(h[i] >> 16);
		out[i * 4 + 2] = (uint8)(h[i] >> 8);
		out[i * 4 + 3] = (uint8)h[i];
	}
	return out;
}

// ---------------------------------------------------------------------------
// HMAC-SHA256 and PBKDF2 (RFC 2104, RFC 8018). The key's inner and outer pad
// states are computed once, so each iteration is two compressions.
// ---------------------------------------------------------------------------

struct Hmac {
	State inner, outer;

	explicit Hmac(const std::string& key) {
		uint8 k[64] = {};
		if (key.size() > 64) {
			Digest d = finish(INITIAL, 0, (const uint8*)key.data(), key.size());
			std::memcpy(k, d.data(), d.size());
		} else {
			std::memcpy(k, key.data(), key.size());
		}
		uint8 ipad[64], opad[64];
		for (int i = 0; i < 64; i++) {
			ipad[i] = k[i] ^ 0x36;
			opad[i] = k[i] ^ 0x5c;
		}
		inner = INITIAL;
		compress(inner, ipad);
		outer = INITIAL;
		compress(outer, opad);
	}

	Digest mac(const uint8* data, size_t len) const {
		Digest in = finish(inner, 64, data, len);
		return finish(outer, 64, in.data(), in.size());
	}
};

Digest pbkdf2(const std::string& plain, const std::vector<uint8>& salt, uint32 iterations) {
	Hmac hmac(plain);
	std::vector<uint8> first(salt);
	first.insert(first.end(), { 0, 0, 0, 1 });  // block index 1: one 32-byte block is all we need
	Digest u = hmac.mac(first.data(), first.size());
	Digest out = u;
	for (uint32 i = 1; i < iterations; i++) {
		u = hmac.mac(u.data(), u.size());
		for (size_t j = 0; j < out.size(); j++)
			out[j] ^= u[j];
	}
	return out;
}

// ---------------------------------------------------------------------------
// Base64 (standard alphabet, no padding) and the stored format.
// ---------------------------------------------------------------------------

const char* B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

std::string b64encode(const uint8* data, size_t len) {
	std::string out;
	for (size_t i = 0; i < len; i += 3) {
		uint32 n = (uint32)data[i] << 16 | (i + 1 < len ? (uint32)data[i + 1] << 8 : 0) | (i + 2 < len ? data[i + 2] : 0);
		out += B64[(n >> 18) & 63];
		out += B64[(n >> 12) & 63];
		if (i + 1 < len) out += B64[(n >> 6) & 63];
		if (i + 2 < len) out += B64[n & 63];
	}
	return out;
}

bool b64decode(const std::string& in, std::vector<uint8>& out) {
	uint32 n = 0;
	int bits = 0;
	for (char c : in) {
		const char* p = std::strchr(B64, c);
		if (c == '\0' || p == nullptr)
			return false;
		n = (n << 6) | (uint32)(p - B64);
		bits += 6;
		if (bits >= 8) {
			bits -= 8;
			out.push_back((uint8)(n >> bits));
		}
	}
	return true;
}

const char PREFIX[] = "$pbkdf2-sha256$";
constexpr uint32 ITERATIONS = 200000;
constexpr size_t SALT_BYTES = 16;

// Compare without stopping at the first difference, so the time a failed
// login takes says nothing about how much of the hash matched.
bool same(const uint8* a, const uint8* b, size_t len) {
	uint8 diff = 0;
	for (size_t i = 0; i < len; i++)
		diff |= a[i] ^ b[i];
	return diff == 0;
}

} // namespace

namespace password {

bool is_hashed(const char* stored) {
	return stored != nullptr && std::strncmp(stored, PREFIX, sizeof(PREFIX) - 1) == 0;
}

std::string hash(const std::string& plain) {
	std::random_device random;  // the OS's generator (/dev/urandom, BCryptGenRandom)
	std::vector<uint8> salt(SALT_BYTES);
	for (auto& byte : salt)
		byte = (uint8)random();
	Digest d = pbkdf2(plain, salt, ITERATIONS);
	return std::string(PREFIX) + std::to_string(ITERATIONS) + "$" + b64encode(salt.data(), salt.size()) + "$" + b64encode(d.data(), d.size());
}

bool verify(const std::string& plain, const char* stored) {
	if (!is_hashed(stored))
		return false;
	std::string rest(stored + sizeof(PREFIX) - 1);
	size_t a = rest.find('$');
	size_t b = a == std::string::npos ? a : rest.find('$', a + 1);
	if (b == std::string::npos)
		return false;
	uint32 iterations = (uint32)std::strtoul(rest.substr(0, a).c_str(), nullptr, 10);
	std::vector<uint8> salt, expected;
	if (iterations == 0 || iterations > 10000000 || !b64decode(rest.substr(a + 1, b - a - 1), salt) || !b64decode(rest.substr(b + 1), expected) || expected.size() != 32)
		return false;
	Digest d = pbkdf2(plain, salt, iterations);
	return same(d.data(), expected.data(), d.size());
}

uint8 flags(const std::string& plain, const std::string& userid) {
	uint8 out = 0;
	bool printable = true;
	for (unsigned char c : plain)
		if (c < 0x20 || c > 0x7e)
			printable = false;
	std::string lower_plain, lower_user, trimmed;
	for (unsigned char c : plain) lower_plain += (char)std::tolower(c);
	for (unsigned char c : userid) lower_user += (char)std::tolower(c);
	size_t first = plain.find_first_not_of(' ');
	trimmed = first == std::string::npos ? "" : plain.substr(first, plain.find_last_not_of(' ') - first + 1);
	// The same rule the app applies before a world is shared (hosting.rs).
	if (plain.size() < 8 || plain.size() > 23 || !printable || trimmed.empty() || lower_plain == lower_user)
		out |= PASSWORD_WEAK;
	if (plain == "ragnarok")
		out |= PASSWORD_DEFAULT;
	return out;
}

} // namespace password
