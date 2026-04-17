import re
import copy


class Lexer:
    def __init__(self):
        TOKEN_SPEC = [
            ("NUMBER", r"\d+"),
            ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("ARROW", r"->"),

            ("LANGLE", r"<"), ("RANGLE", r">"),
            ("LBRACE", r"\{"), ("RBRACE", r"\}"),
            ("LPAREN", r"\("), ("RPAREN", r"\)"),
            ("LBOX", r"\["), ("RBOX", r"\]"),
            ("TSTRING", r'"[^"]*"'), ("OSTRING", r"'[^']*'"),

            ("SEMICOLON", r";"),
            ("COLON", r":"),
            ("POINT", r"\."), ("COMMA", r"\,"),
            ("ASSIGN", r"="),
            ("PLUS", r"\+"), ("MINUS", r"\-"),
            ("SKIP", r"[ \t\n]+"),
            ("MISMATCH", r"."),
        ]
        self.TOKEN_RE = re.compile("|".join(f"(?P<{n}>{r})" for n, r in TOKEN_SPEC))

    def lex(self, code):
        tokens = []
        for m in self.TOKEN_RE.finditer(code):
            kind = m.lastgroup
            value = m.group()
            if kind == "SKIP":
                continue
            if kind == "MISMATCH":
                raise SyntaxError(f"Unexpected token: {value}")
            tokens.append((kind, value))
        tokens.append("END")
        return tokens


# AST - classes


class GMemory:
    def __init__(self, typ, name):
        self.typ = typ
        self.name = name

    def __repr__(self):
        return f"GMemory({self.typ}, {self.name})"


class LMemory:
    def __init__(self, typ, name, local_socket, local_func=None):
        self.typ = typ
        self.name = name
        self.local_socket = local_socket
        self.local_func = local_func

    def __repr__(self):
        return f"LMemory({self.typ}, {self.name}, {self.local_socket}, {self.local_func})"


class Function:
    def __init__(self, name, ret_type):
        self.name = name
        self.ret_type = ret_type
        self.locals = []
        self.body = []

    def __repr__(self):
        return f"Function({self.name}, {self.ret_type})"


class Call:
    def __init__(self, socket, name, args):
        self.socket = socket
        self.name = name
        self.args = args

    def __repr__(self):
        return f"Call({self.socket}. {self.name}, {self.args})"


class CallVar:
    def __init__(self, socket, name):
        self.socket = socket
        self.name = name

    def __repr__(self):
        return f"CallVar({self.socket}, {self.name})"


class EditVar:
    def __init__(self, socket, name, expr):
        self.socket = socket
        self.name = name
        self.expr = expr

    def __repr__(self):
        return f"EditVar({self.socket}, {self.name}, {self.expr})"


class VarDecl:
    def __init__(self, typ, name, expr=None):
        self.typ = typ
        self.name = name
        self.expr = expr

    def __repr__(self):
        return f"VarDecl({self.typ}, {self.name}, {self.expr})"


# compil - tokens to AST
class Parser:
    def __init__(self, code):
        self.tokens = Lexer().lex(code)
        self.pos = 0
        self.var_pos = 1
        self.memory = {}

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def socket_exists(self, name):
        return name in self.memory

    def variable_exists(self, socket, name):
        return name in self.memory[socket]["v"]

    def peekahead(self, counter):
        return self.tokens[self.pos + counter] if self.pos <= len(self.tokens) else None

    def consume(self, kind=None):
        tok = self.peek()
        if kind:
            if not tok or tok[0] != kind:
                raise SyntaxError(f"Expected {kind}, got {tok}")
        if self.peek() == "END": return None
        self.pos += 1
        return tok[1]

    def parse(self):
        while self.peek() != "END":
            if self.peek()[1] == "memory":
                self.memory_d()
            elif self.peek()[1] == "include":
                self.include_d()
            elif self.peek()[1] == "def":
                self.function_d()
            else:
                print(self.peek())
                raise SyntaxError("Unexpected token")
        return self.memory

    def memory_d(self):
        """управление памятью"""

        self.consume("IDENT")  # memory
        self.consume("LANGLE")
        memory_global = self.consume("IDENT")
        typ = self.consume("IDENT")
        name = self.consume("IDENT")
        self.consume("RANGLE")
        self.consume("SEMICOLON")
        if memory_global == "global":
            self.create_memory_socket(GMemory(typ, name))
        else:
            raise TypeError("the local memory in the global area is specified")

    def include_d(self):
        """импорт"""
        self.consume("IDENT")  # include
        self.consume("LANGLE")
        lib = self.consume("IDENT")
        self.consume("RANGLE")
        self.consume("SEMICOLON")
        self.create_memory_socket(GMemory("f", lib))
        timed = """memory <global f print>;
def <print print> [data:str] -> void {
            print.print <data>;
}
        """
        parser = Parser(timed)
        parser.parse()

        self.Add_to_memory_socket(lib, "f", name, expr=parser.memory)

    def function_d(self):
        """управление функцией"""
        vars = None
        self.consume("IDENT")
        self.consume("LANGLE")
        socket = self.consume("IDENT")
        name = self.consume("IDENT")
        self.consume("RANGLE")
        if self.peek()[0] == "LBOX":
            self.consume("LBOX")

            vars = []
            while self.peek()[0] != "RBOX":
                print(self.peek())
                pos = self.var_pos
                self.var_pos += 1
                name_var = self.consume("IDENT")
                self.consume("COLON")
                typ = self.consume("IDENT")
                if self.peek()[0] != "RBOX": self.consume("COMMA")
                vars.append((pos, name_var, typ))
            self.consume("RBOX")
        self.consume("ARROW")
        ret_type = self.consume("IDENT")
        self.consume("LBRACE")

        fn = Function(name, ret_type)
        self.Add_to_memory_socket(socket, "f", name, expr=None, varses_base=f"{name}_var")
        if vars != None and vars != []:
            self.create_memory_socket(LMemory("v", f"{name}_var", socket, local_func=name))
            for var in vars:
                print(socket, "v", var[1], f"{name}_var", var[0], var[2], "l")
                self.Add_to_memory_socket(socket, "v", var[1], local_socket=f"{name}_var", local_func=name, pos=var[0],
                                          type_var=var[2], type="l")
        expr = []
        expr_calls = []
        print(self.memory)
        while self.peek()[0] != "RBRACE":
            # print(self.pos, "\n", self.peek())
            # print(self.peek())
            expr.append(self.parse_stmt())
        for string in expr:
            if string != None:
                expr_calls.append(string)

        print(expr)
        if expr_calls != []: self.Add_to_memory_socket(socket, "f", name, expr=expr_calls, varses_base=f"{name}_var")

        self.consume("RBRACE")

    def parse_stmt(self):
        """
        основной парсинг строки
        """

        if (self.peek()[0] == "IDENT"
                and self.peekahead(1)[0] == "COLON"
                and self.peekahead(2)[0] == "IDENT"
                and self.peekahead(3)[0] == "IDENT"
                or self.peekahead(1)[0] == "POINT"
                and self.peekahead(2)[0] == "IDENT"

        ):

            is_local = False
            local_func = None
            local_socket = None
            pos = self.var_pos
            self.var_pos += 1

            socket = self.consume("IDENT")
            if self.peek()[0] == "POINT":
                is_local = True
                if self.peekahead(2)[0] == "POINT":
                    self.consume("POINT")
                    local_func = self.consume("IDENT")
                self.consume("POINT")
                local_socket = self.consume("IDENT")

            if is_local and not local_socket: raise SyntaxError("the local socket is not specified")

            self.consume("COLON")
            typ = self.consume("IDENT")
            name = self.consume("IDENT")
            if self.peek()[0] == "ASSIGN":
                self.consume("ASSIGN")
                expr = self.parse_expr()
                if is_local == False:
                    self.Add_to_memory_socket(socket, "v", name, expr=expr, pos=pos, type_var=typ)
                elif is_local and local_func:
                    self.create_memory_socket(LMemory("v", local_socket, socket, local_func=local_func))
                    self.Add_to_memory_socket(socket, "v", name, expr=expr, pos=pos, type_var=typ, type="l",
                                              local_func=local_func, local_socket=local_socket)
                elif is_local and not local_func:
                    self.create_memory_socket(LMemory("v", local_socket, socket, local_func=local_func))
                    self.Add_to_memory_socket(socket, "v", name, expr=expr, pos=pos, type_var=typ, type="l",
                                              local_socket=socket)
                return None
            else:
                self.consume("SEMICOLON")
                if is_local == False:
                    self.Add_to_memory_socket(socket, "v", name, pos=pos, type_var=typ)
                elif is_local and local_func:
                    self.Add_to_memory_socket(socket, "v", name, pos=pos, type_var=typ, type="l",
                                              local_func=local_func, local_socket=socket)
                elif is_local and not local_func:
                    self.Add_to_memory_socket(socket, "v", name, pos=pos, type_var=typ, type="l",
                                              local_socket=socket)
                return None

        if self.peek()[0] == "IDENT" and self.peekahead(1)[0] == "IDENT" and self.peekahead(2)[0] == "ASSIGN":
            if not self.peek()[1] in self.memory: raise SyntaxError(f"a non-existent socket was specified")
            if not self.peekahead(1)[1] in self.memory[self.peek()[1]]["v"]: raise SyntaxError(
                "a variable that does not exist in the specified socket was called")
            """editing variable

            self.peek()[0] == "IDENT" = socket
            self.peakahead(1)[0] == "IDENT" = name
            self.peakahead(2)[0] == "ASSIGN" = clarifying what the programmer wants to change in the variable

            if not self.peek()[0] in self.memory = checking the existence of a socket in memory
            if not self.peakahead(1)[0] in self.memory[self.peek()[0] == "IDENT"] = checking the existence of a variable in the specified socket
            """
            socket = self.consume("IDENT")
            name_var = self.consume("IDENT")
            self.consume("ASSIGN")
            return EditVar(socket, name_var, self.parse_expr())

        if self.peek()[0] == "IDENT" and self.peekahead(1)[0] == "POINT" and self.peekahead(2)[0] == "IDENT" and \
                self.peekahead(3)[0] == "LANGLE":
            return self.parse_expr()

    def parse_expr(self):
        if self.peek()[0] == "TSTRING" or self.peek()[0] == "OSTRING":
            ret = self.consume()
            self.consume("SEMICOLON")
            return ret[1:-1]
        if self.peek()[0] == "NUMBER":
            val = int(self.consume("NUMBER"))
            self.consume("SEMICOLON")
            return val

        if self.peek()[0] == "IDENT" and self.peekahead(1)[0] == "POINT" and self.peekahead(2)[0] == "IDENT" and \
                self.peekahead(3)[0] == "LANGLE":
            socket = self.consume("IDENT")
            self.consume("POINT")
            name = self.consume("IDENT")
            self.consume("LANGLE")

            expr = []
            while self.peek()[0] != "RANGLE":
                expr.append(self.peek()[1])
                self.consume()
            self.consume("RANGLE")
            self.consume("SEMICOLON")

            return Call(socket, name, expr)

        if (self.peek()[0] == "IDENT"
                and self.peekahead(1)[0] == "POINT"
                and self.peekahead(2)[0] == "IDENT"
                and self.peekahead(3)[0] == "SEMICOLON"):
            socket = self.consume("IDENT")
            self.consume("POINT")
            name = self.consume("IDENT")
            self.consume("SEMICOLON")
            return CallVar(socket, name)

    def create_memory_socket(self, _class):
        """socket tamplate:

    {Name_socket : {_class : Mamory(name, typ), v:{} or f:{}}}

    if type getted "v" but socket have type "f" тогда reterned "TYPE ERROR"

    this will saved in self.memory.

    ::return:: None, socket saved in memory.
        """
        if _class.typ not in ["v", "f"]: raise SyntaxError("unknown socket type")
        if _class.typ == "v":
            socket = {"class": _class, "v": {}, "ls": {}}

        elif _class.typ == "f":
            socket = {"class": _class, "f": {}, "ls": {}}

        # elif _class.__class__.__name__ == "LMemory": socket = {"class": _class, "b": {}}

        else:
            raise SyntaxError("the socket type is not specified")
        if _class.__class__.__name__ == "LMemory":
            print("1", _class)
            if _class.local_func:
                self.memory[_class.local_socket]["f"][_class.local_func]["ls"][_class.name] = socket
            else:
                self.memory[_class.local_socket]["ls"][_class.name] = socket
        elif not _class.name in self.memory:
            self.memory[_class.name] = socket
        else:
            raise SyntaxError("a socket with that name already exists")

    def Add_to_memory_socket(self, socet, type_class, name, expr=None, local_func=None, local_socket=None, type=None,
                             pos=None, type_var=None, varses_base=None):
        """

        :param socet: имя изменяемого ГЛОБАЛЬНОГО сокета
        :param type_class: тип изменяемого сокета
        :param name: имя создаваемого объекта
        :param expr: необходимая информация (если есть)
        :param local_func: локальная функция, необходимая для изменения локальных сокетов
        :param local_socket: имя локального сокета при изменении его
        :param pos: позиция для переменных
        :param type: необходим для изменения локальных сокетов для того чтобы не получать ошибку об несуществовании сокета
        :param varses_base: имя локального хранилища переменных. необходим для вызова самой функции, есть в ней в том случае если у функции есть входные переменные
        :return: изменяет сокет в памяти, является последней ступенькой в работе парсера
        """

        if not socet in self.memory: raise SyntaxError(f"Socket {socet} is not defined")

        if type_class == "f":

            if "f" not in self.memory[socet]:
                raise TypeError("a socket of the wrong type is selected")
            else:
                if type == None and varses_base != None:
                    self.memory[socet]["f"][name] = {"expr": expr, "db": varses_base, "ls": {}}
                elif type == None and varses_base == None:
                    self.memory[socet]["f"][name] = {"expr": expr}
                elif type == "l":

                    if local_func != None:
                        self.memory[socet]["f"][local_func]["ls"][local_socket] = {"expr": expr}
                    elif local_func == None:
                        self.memory[socet]["ls"][local_socket] = {"expr": expr}
        if type_class == "v":
            if "v" not in self.memory[socet] and type != "l":
                raise TypeError("a socket of the wrong type is selected")
            elif type == "l":
                if local_func != None:
                    print(1)
                    self.memory[socet]["f"][local_func]["ls"][local_socket]["v"][name] = expr
                elif local_func == None:
                    print(2)
                    self.memory[socet]["ls"][local_socket]["v"] = expr
            else:
                if pos == None: raise SyntaxError("pos is not set")
                self.memory[socet]["v"][name] = {"expr": expr, "pos": pos}


class IR:
    def __init__(self):
        self.ir_code = []

    def _repr(self):
        code = ""
        for i in self.ir_code:
            code += i
            code += "\n"
        return f"IR:\n{code}"

    def add_string(self, operation, socket, args):
        self.ir_code.append(f"{operation} {socket}:{args}")


class IRC:
    def __init__(self, memory):
        self.ir = IR()
        self.memory = memory

    def compile(self):
        for socket in self.memory:
            print(socket)
            if self.memory[socket]["class"].typ == "v":

                for var in self.memory[socket]["v"]:
                    self.ir.add_string("сvar", socket,
                                       f"{self.memory[socket]["v"][var]["expr"]} ({self.memory[socket]["v"][var]["pos"]})")

            if self.memory[socket]["class"].typ == "f":
                print(self.memory[socket]["class"])
                for func in self.memory[socket]["f"]:
                    print(self.memory[socket]["class"])
                    for expr in self.memory[socket]["f"][func]:
                        for operation in self.memory[socket]["f"][func][expr]:
                            oper = operation.__class__.__name__
                            if oper == "Call":
                                socket = operation.socket
                                operations = "Call"
                                args = (operation.args, operation.name)
                                self.ir.add_string(operations, socket, args)
                            if oper == "EditVar":
                                socket = operation.socket
                                operas = "EditVar"
                                args = (operation.expr, operation.name)
                                self.ir.add_string(operas, socket, args)



















