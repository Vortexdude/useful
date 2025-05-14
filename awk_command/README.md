

### 📄 **AWK**

`awk` is a powerful text-processing tool commonly used for pattern scanning, data extraction, and reporting. It reads input line-by-line, splits each line into fields, and allows processing with pattern-action pairs.

## 🔹 Basic Syntax

```bash
awk 'pattern { action }' file
````

If `pattern` is omitted, the `action` is applied to all lines.

---

## 📥 Input Splitting

By default, `awk` splits input lines on whitespace.

| Variable | Description                                  |
| -------- | -------------------------------------------- |
| `$0`     | Entire current line                          |
| `$1`     | First field                                  |
| `$2`     | Second field                                 |
| `NF`     | Number of fields in the current line         |
| `NR`     | Number of current input record (line number) |
| `FS`     | Field separator (default: space)             |
| `OFS`    | Output field separator                       |

---

## ✅ Common Examples

### Print Specific Columns

```bash
awk '{print $1, $3}' file.txt
```

### Use a Custom Field Separator (CSV)

```bash
awk -F, '{print $2}' data.csv
```

### Print Lines Matching a Pattern

```bash
awk '/error/ {print}' logfile.log
```

### Only Print Lines with More Than 3 Fields

```bash
awk 'NF > 3' file.txt
```

### Print Line Numbers

```bash
awk '{print NR, $0}' file.txt
```

---

## 🔁 Arithmetic and Logic

```bash
awk '{sum += $1} END {print "Total:", sum}'
```

```bash
awk '$2 > 100' data.txt   # Print lines where 2nd column > 100
```

---

## 🧠 BEGIN and END Blocks

```bash
awk 'BEGIN {print "Start"} {print} END {print "End"}' file.txt
```

---

## 🧰 Built-in Functions

| Function          | Description                |
| ----------------- | -------------------------- |
| `length($1)`      | Length of field 1          |
| `tolower($1)`     | Convert to lowercase       |
| `toupper($1)`     | Convert to uppercase       |
| `substr($1,2,3)`  | Substring of field 1       |
| `index($1,"abc")` | Position of substring      |
| `split($1,a,",")` | Split field into array `a` |

---

## 🔧 Advanced Examples

### Sum Column 3 Only If Column 1 is 'foo'

```bash
awk '$1 == "foo" {sum += $3} END {print sum}' file.txt
```

### Replace Tabs with Commas

```bash
awk '{gsub(/\t/, ","); print}' file.txt
```

### Print Unique Values from Column 2

```bash
awk '!seen[$2]++ {print $2}' file.txt
```

---

## 🔄 In-Place File Edits (with `awk` & `sponge` from `moreutils`)

```bash
awk '{gsub("foo", "bar"); print}' file.txt | sponge file.txt
```

---

## 🧱 Writing an AWK Script File

**myscript.awk**

```awk
BEGIN { FS = ","; OFS = "," }
$3 > 100 { print $1, $2, "PASS" }
$3 <= 100 { print $1, $2, "FAIL" }
```

**Usage:**

```bash
awk -f myscript.awk scores.csv
```

---

## 📑 Summary of Useful One-liners

| Task                        | One-liner                                            |
| --------------------------- | ---------------------------------------------------- |
| Print line numbers          | `awk '{print NR, $0}' file`                          |
| Count lines                 | `awk 'END {print NR}' file`                          |
| Print first column          | `awk '{print $1}' file`                              |
| Sum column 1                | `awk '{sum+=$1} END {print sum}' file`               |
| Find max in column 2        | `awk 'max < $2 { max = $2 } END { print max }' file` |
| Filter pattern              | `awk '/pattern/ { print }' file`                     |
| Print lines > 80 characters | `awk 'length($0) > 80' file`                         |

---

