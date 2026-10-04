#Requires AutoHotkey v2.0

^+b::
{
    text := A_Clipboard

    ; Replace all OCR line breaks with spaces
    text := StrReplace(text, "`r`n", " ")
    text := StrReplace(text, "`n", " ")
    text := StrReplace(text, "`r", " ")

    ; Collapse multiple spaces/tabs into one
    text := RegExReplace(text, "[ \t]+", " ")

    ; JSON-escape special characters
    text := StrReplace(text, "\", "\\")
    text := StrReplace(text, '"', '\"')
    text := StrReplace(text, "`b", "\b")
    text := StrReplace(text, "`f", "\f")
    text := StrReplace(text, "`n", "\n")
    text := StrReplace(text, "`r", "\r")
    text := StrReplace(text, "`t", "\t")

    ; Remove spaces at beginning/end
    text := Trim(text)

    ; Put cleaned version back on clipboard
    A_Clipboard := text

    ; Paste it
    Send "^v"
}