import argparse
import http.cookiejar
import json
import random
import time
import urllib.request

PERSONAS = [
    ("student", 0.09),
    ("busy_professional", 0.14),
    ("small_business_owner", 0.17),
    ("price_sensitive", 0.08),
    ("early_adopter", 0.20),
]


def clamp(x, low=0.0, high=1.0):
    return max(low, min(high, x))


def one_user(base_url, persona, base_probability, effect, rng):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    url = f"{base_url}/?source=virtual&persona={persona}"

    with opener.open(url, timeout=5) as response:
        variant = response.headers.get("X-AB-Variant")
        response.read()

    probability = base_probability + (effect if variant == "B" else 0.0)
    probability = clamp(probability)
    clicked = rng.random() < probability

    if clicked:
        req = urllib.request.Request(
            f"{base_url}/api/click",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with opener.open(req, timeout=5) as response:
            response.read()

    return variant, clicked, probability


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic A/B traffic")
    parser.add_argument("--users", type=int, default=1000, help="Number of virtual visitors")
    parser.add_argument("--effect", type=float, default=0.03, help="Absolute conversion uplift for B; 0.03 = +3 percentage points")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatable demo")
    parser.add_argument("--url", default="http://127.0.0.1:5000", help="A/B app URL")
    parser.add_argument("--delay", type=float, default=0.0, help="Optional delay between users in seconds")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    counts = {"A": {"n": 0, "c": 0}, "B": {"n": 0, "c": 0}}

    print(f"Simulating {args.users} users | B true effect = {args.effect:+.1%} absolute | seed={args.seed}")
    print("Persona distribution and baseline conversion are identical before A/B randomization.\n")

    for i in range(1, args.users + 1):
        persona, base_probability = rng.choice(PERSONAS)
        variant, clicked, probability = one_user(
            args.url, persona, base_probability, args.effect, rng
        )
        counts[variant]["n"] += 1
        counts[variant]["c"] += int(clicked)

        if i % max(1, args.users // 10) == 0 or i == args.users:
            a = counts["A"]
            b = counts["B"]
            a_rate = a["c"] / a["n"] if a["n"] else 0
            b_rate = b["c"] / b["n"] if b["n"] else 0
            print(f"{i:>5}/{args.users} | A {a['c']}/{a['n']} ({a_rate:.1%}) | B {b['c']}/{b['n']} ({b_rate:.1%})")

        if args.delay:
            time.sleep(args.delay)

    with urllib.request.urlopen(f"{args.url}/api/results", timeout=5) as response:
        results = json.load(response)

    print("\nFinal server-side analysis:")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
