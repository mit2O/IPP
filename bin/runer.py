import compiller as cmp
import ASTprint as ap

code = """
memory <global f io>;

def <io print> [data:str] -> void {

    io.print.hello: str hello = "hello world!";
}


"""



lex = cmp.Lexer().lex(code)
print(lex)
parser = cmp.Parser(code)
parser.parse()
print(ap.dump(parser.memory))
ir = cmp.IRC(parser.memory)
ir.compile()
ir_raw = ir.ir.ir_code

print(ir_raw)






