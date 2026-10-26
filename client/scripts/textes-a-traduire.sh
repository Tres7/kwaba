#!/usr/bin/env bash
# Finds the lines that probably contain text displayed in French (helps the i18n extraction)
for f in "$@"; do
  echo "=== $f"
  grep -nE '[éèàçêôûÉÀ]|"[A-Z][a-z]+[ ,.!?]|>[A-Z][a-zé]|^\s+[A-ZÀ-Ý][a-zà-ÿ’'"'"']+[ ,.!?:]|aria-label="|placeholder="|label="|title="|hint="|toast\.|toLocale|"fr-FR"' "$f" \
    | grep -vE '^\s*[0-9]+:\s*(//|\*|/\*|\{/\*)|^[0-9]+:import|className="[^"]*"$|t\("' 
done
