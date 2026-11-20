#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec relate serve --database jobradar.rl --mcp stdio --read-only
