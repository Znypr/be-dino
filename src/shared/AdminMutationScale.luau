--!strict
-- BD-237 / docs/115: the playtest-only admin "Mutation chance" multiplier is PER PLAYER. A book maps a Player (any table key) to the
-- scale that player's own catches roll at; everyone else is x1. Pure and weak-keyed so it is unit tested (verify_admin) and a
-- left Player is dropped. Server memory only: nothing here is ever saved or sent to a client.
local Scale = {}
export type Book = {scales: {[any]: number}}

function Scale.new(): Book
    return {scales = setmetatable({}, {__mode = "k"}) :: any}
end
-- value is clamped to x1..x10; x1 (or a non-number / NaN) removes the entry, so the default stays implicit.
function Scale.set(book: Book, key: any, value: any)
    local scale = if typeof(value) == "number" and value == value then math.clamp(value, 1, 10) else 1
    book.scales[key] = if scale > 1 then scale else nil
end
function Scale.clear(book: Book, key: any) book.scales[key] = nil end
function Scale.clearAll(book: Book) table.clear(book.scales) end
function Scale.get(book: Book, key: any): number return book.scales[key] or 1 end

return Scale
