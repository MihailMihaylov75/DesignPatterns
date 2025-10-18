from behavioral.command.text_editor_command import TextBuffer, InsertText, MacroCommand, Invoker


def test_insert_and_undo():
    buf = TextBuffer()
    cmd = InsertText(buf, "Hi")
    cmd.execute()
    assert buf.text == "Hi"
    cmd.undo()
    assert buf.text == ""


def test_macro_execute_and_undo():
    buf = TextBuffer()
    macro = MacroCommand([InsertText(buf, "Hello"), InsertText(buf, " "), InsertText(buf, "World")])
    macro.execute()
    assert buf.text == "Hello World"
    macro.undo()
    assert buf.text == ""


def test_invoker_undo_redo():
    buf = TextBuffer()
    inv = Invoker()
    inv.run(InsertText(buf, "A"))
    inv.run(InsertText(buf, "B"))
    assert buf.text == "AB"
    assert inv.undo() is True
    assert buf.text == "A"
    assert inv.redo() is True
    assert buf.text == "AB"
