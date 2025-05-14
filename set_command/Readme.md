# Bash `set` Command Cheat Sheet

The `set` command in Bash is used to modify shell behavior, manage positional parameters, and list shell variables. This guide breaks down its usage with examples.

---

## 🔧 1. Shell Option Flags

These change the behavior of the Bash shell.

| Flag      | Long Name   | Description                                                    |
| --------- | ----------- | -------------------------------------------------------------- |
| `-e`      | `errexit`   | Exit immediately if a command exits with a non-zero status.    |
| `-x`      | `xtrace`    | Print each command and its arguments as they are executed.     |
| `-u`      | `nounset`   | Treat unset variables as an error when substituting.           |
| `-o`      | `<option>`  | Use long-form options like `-o pipefail`, `-o noclobber`, etc. |
| `-n`      | `noexec`    | Read commands but don't execute them (syntax checking).        |
| `-v`      | `verbose`   | Print shell input lines as they are read.                      |
| `-f`      | `noglob`    | Disable filename expansion (globbing).                         |
| `-C`      | `noclobber` | Prevent overwriting files with `>` redirection.                |
| `+<flag>` |             | Disable the corresponding shell option.                        |

### ✅ Examples

```bash
set -e               # Stop script on error
set -u               # Treat unset variables as errors
set -x               # Debug mode: print commands before running
set -euo pipefail    # Safe mode: strict error handling
set +x               # Turn off debug mode
set -o noclobber     # Prevent overwriting files
set +o noclobber     # Allow overwriting files
```

---

## 📥 2. Setting Positional Parameters

You can set `$1`, `$2`, etc. manually using `set`.

### ✅ Example

```bash
set alpha beta gamma
echo "$1"  # alpha
echo "$2"  # beta
```

You can reset them with `set --`:

```bash
set -- foo bar
echo "$1"  # foo
echo "$2"  # bar
```

---

## 📋 3. Listing Variables

Run without arguments, `set` prints all shell variables and functions in alphabetical order.

### ✅ Example

```bash
set
```

*Note: This produces a very long output.*

---

## 🔄 4. Combining Options and Positional Parameters

Options must come first when combining.

### ✅ Example

```bash
set -x -- one two three
```

This enables debug mode and sets `$1`, `$2`, `$3`.

---

## 🛠️ 5. Resetting Options

Disable a previously set option using `+`.

### ✅ Example

```bash
set +e  # Turn off 'exit on error'
```

---

## 🧾 6. Using `-o` with Long Options

| Option      | Description                             |
| ----------- | --------------------------------------- |
| `pipefail`  | Exit if any command in a pipeline fails |
| `noclobber` | Prevent overwriting with `>`            |
| `allexport` | Export all variables to environment     |

### ✅ Example

```bash
set -o pipefail
set +o pipefail
```

---

## 📑 Summary of Useful Flag Combos

| Command                 | Purpose                                |
| ----------------------- | -------------------------------------- |
| `set -euo pipefail`     | Strict error handling in scripts       |
| `set -x`                | Debug mode: show each command          |
| `set +x`                | Turn off debug mode                    |
| `set -- arg1 arg2 arg3` | Set positional parameters              |
| `set -o noclobber`      | Prevent file overwrites with `>`       |
| `set`                   | List all shell variables and functions |

---

Let me know if you need this converted into a downloadable file!
