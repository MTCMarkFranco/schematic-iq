# JSON Output Rules (Shared)

These rules apply to ALL stages that produce JSON output:

1. **Valid JSON only** — Output must be parseable JSON. No trailing commas, no comments.
2. **UTF-8 encoding** — All text must be valid UTF-8.
3. **Consistent naming** — Use snake_case for all keys.
4. **No null arrays** — Use empty arrays `[]` instead of `null` for list fields.
5. **Stable ordering** — Arrays of objects should maintain consistent ordering across runs where possible.
6. **No extra fields** — Only include fields defined in the schema. Do not add custom keys.
