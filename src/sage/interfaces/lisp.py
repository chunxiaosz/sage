r"""
Lisp Interface

EXAMPLES:
    sage: lisp.eval('(* 4 5)')
    '20'
    sage: a = lisp(3); b = lisp(5)
    sage: a + b
    8
    sage: a * b
    15
    sage: a / b
    3/5
    sage: a - b
    -2
    sage: a.sin()
    0.14112
    sage: b.cos()
    0.2836622
    sage: a.exp()
    20.085537
    sage: lisp.eval('(+ %s %s)'%(a.name(), b.name()))
    '8'

One can define functions and the interface supports object-oriented
notation for calling them:
    sage: lisp.eval('(defun factorial (n) (if (= n 1) 1 (* n (factorial (- n 1)))))')
    'FACTORIAL'
    sage: lisp('(factorial 10)')
    3628800
    sage: lisp(10).factorial()
    3628800
    sage: a = lisp(17)
    sage: a.factorial()
    355687428096000

AUTHORS:
    -- William Stein (first version)
    -- William Stein (2007-06-20): significant improvements.
"""

##########################################################################
#
#       Copyright (C) 2006 William Stein <wstein@gmail.com>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#                  http://www.gnu.org/licenses/
#
##########################################################################

from __future__ import with_statement

import random

from expect import Expect, ExpectElement, ExpectFunction, FunctionElement, gc_disabled, AsciiArtString
from sage.misc.misc import verbose, UNAME, is_64bit
from sage.structure.element import RingElement

class Lisp(Expect):
    def __init__(self,
                 maxread=100000, script_subdirectory=None,
                 logfile=None,
                 server=None,
                 server_tmpdir=None):
        """
        EXAMPLES:
            sage: lisp == loads(dumps(lisp))
            True
        """
        Expect.__init__(self,

                        # The capitalized version of this is used for printing.
                        name = 'Lisp',

                        # This is regexp of the input prompt.  If you can change
                        # it to be very obfuscated that would be better.   Even
                        # better is to use sequence numbers.
                        prompt = '\[[0-9]+\]> ',

                        # This is the command that starts up your program
                        command = "clisp --silent -on-error abort",

                        maxread = maxread,
                        server=server,
                        server_tmpdir=server_tmpdir,
                        script_subdirectory = script_subdirectory,

                        # If this is true, then whenever the user presses Control-C to
                        # interrupt a calculation, the whole interface is restarted.
                        restart_on_ctrlc = False,

                        # If true, print out a message when starting
                        # up the command when you first send a command
                        # to this interface.
                        verbose_start = False,

                        logfile=logfile,

                        # If an input is longer than this number of characters, then
                        # try to switch to outputing to a file.
                        eval_using_file_cutoff=1024)

        self.__seq = 0
        self.__in_seq = 1

    def eval(self, code, strip=True):
        """
        EXAMPLES:
            sage: lisp.eval('(+ 2 2)')
            '4'
        """
        with gc_disabled():
            self._synchronize()
            code = str(code)
            code = code.strip()
            code = code.replace('\n',' ')
            x = []
            for L in code.split('\n'):
                if L != '':
                    try:
                        s = self.__in_seq + 1
                        pr = '\[%s\]>'%s
                        M = self._eval_line(L, wait_for_prompt=self._prompt)
                        phrase = '[C\x1b[C\n'
                        phrase = phrase if phrase in M else L
                        i = M.rfind(phrase)
                        if i > 1:
                            M = M[i+len(phrase):]
                        x.append(M.strip())
                        self.__in_seq = s
                    except KeyboardInterrupt:
                        # DO NOT CATCH KeyboardInterrupt, as it is being caught
                        # by _eval_line
                        # In particular, do NOT call self._keyboard_interrupt()
                        raise
                    except TypeError, s:
                        return 'error evaluating "%s":\n%s'%(code,s)
            return '\n'.join(x)

    def set(self, var, value):
        """
        Set the variable var to the given value.

        EXAMPLES:
            sage: lisp.set('x', '2')
            sage: lisp.get('x')
            '2'
        """
        cmd = '(setq %s %s)'%(var, value)
        out = self.eval(cmd)
        if '***' in out:
            raise TypeError, "Error executing code in SAGE\nCODE:\n\t%s\nSAGE ERROR:\n\t%s"%(cmd, out)

    def get(self, var):
        """
        EXAMPLES:
            sage: lisp.set('x', '2')
            sage: lisp.get('x')
            '2'
        """
        out = self.eval(var).lstrip().lstrip(var).lstrip()
        return out

    def _start(self, *args, **kwds):
        """
        EXAMPLES:
            sage: l = Lisp()
            sage: l.is_running()
            False
            sage: l._start()
            sage: l.is_running()
            True
        """
        Expect._start(self, *args, **kwds)
        self.__in_seq = 1

    def _synchronize(self):
        E = self._expect
        if E is None:
            self._start()
            E = self._expect
        r = random.randrange(2147483647)
        s = str(r+1)
        cmd = "(+ 1 %s)\n"%r
        E.sendline(cmd)
        E.expect(s)
        E.expect(self._prompt)

    def _repr_(self):
        """
        EXAMPLES:
            sage: lisp
            Lisp Interpreter
        """
        return 'Lisp Interpreter'

    def __reduce__(self):
        """
        EXAMPLES:
            sage: lisp.__reduce__()
            (<function reduce_load_Lisp at 0x...>, ())

        """
        return reduce_load_Lisp, tuple([])

    def _function_class(self):
        """
        EXAMPLES:
            sage: lisp._function_class()
            <class 'sage.interfaces.lisp.LispFunction'>
         """
        return LispFunction

    def _quit_string(self):
        """
        EXAMPLES:
            sage: lisp._quit_string()
            '(quit);'

            sage: l = Lisp()
            sage: l._start()
            sage: l.quit()
            sage: l.is_running()
            False
        """
        return '(quit);'

    def _read_in_file_command(self, filename):
        """
        EXAMPLES:
            sage: lisp._read_in_file_command(tmp_filename())
            Traceback (most recent call last):
            ...
            NotImplementedError
        """
        raise NotImplementedError

    def trait_names(self):
        """
        EXAMPLES:
            sage: lisp.trait_names()
            Traceback (most recent call last):
            ...
            NotImplementedError

        """
        raise NotImplementedError

    def kill(self, var):
        """
        EXAMPLES:
            sage: lisp.kill('x')
            Traceback (most recent call last):
            ...
            NotImplementedError
        """
        raise NotImplementedError

    def console(self):
        """
        Spawn a new Lisp command-line session.

        EXAMPLES:
            sage: lisp.console() #not tested
              i i i i i i i       ooooo    o        ooooooo   ooooo   ooooo
              I I I I I I I      8     8   8           8     8     o  8    8
              I  \ `+' /  I      8         8           8     8        8    8
               \  `-+-'  /       8         8           8      ooooo   8oooo
                `-__|__-'        8         8           8           8  8
                    |            8     o   8           8     o     8  8
              ------+------       ooooo    8oooooo  ooo8ooo   ooooo   8
            ...
        """
        lisp_console()


    def version(self):
        """
        Returns the version of Lisp being used.

        EXAMPLES:
            sage: lisp.version()
            GNU CLISP ... (...) (built ...) (memory ...)
            ...

        """
        import subprocess
        p = subprocess.Popen('clisp --version', shell=True, stdin=subprocess.PIPE,
                             stdout = subprocess.PIPE, stderr=subprocess.PIPE)
        return AsciiArtString(p.stdout.read())

    def _object_class(self):
        """
        EXAMPLES:
            sage: lisp._object_class()
            <class 'sage.interfaces.lisp.LispElement'>

        """
        return LispElement

    def _function_class(self):
        """
        EXAMPLES:
            sage: lisp._function_class()
            <class 'sage.interfaces.lisp.LispFunction'>
        """
        return LispFunction

    def _function_element_class(self):
        """
        EXAMPLES:
            sage: lisp._function_element_class()
            <class 'sage.interfaces.lisp.LispFunctionElement'>
        """
        return LispFunctionElement

    def _true_symbol(self):
        """
        EXAMPLES:
            sage: lisp._true_symbol()
            'T'
        """
        return 'T'

    def _false_symbol(self):
        """
        EXAMPLES:
            sage: lisp._false_symbol()
            'NIL'
        """
        return 'NIL'

    def _equality_symbol(self):
        """
        We raise a NotImplementedError when _equality_symbol is called since
        equality testing in Lisp does not use infix notation and cannot be
        done the same way as in the other interfaces.

        EXAMPLES:
            sage: lisp._equality_symbol()
            Traceback (most recent call last):
            ...
            NotImplementedError: ...
        """
        raise NotImplementedError, ("We should never reach here in the Lisp interface. " +
                                    "Please report this as a bug.")

    def help(self, command):
        """
        EXAMPLES:
            sage: lisp.help('setq')
            Traceback (most recent call last):
            ...
            NotImplementedError
        """
        raise NotImplementedError

    def function_call(self, function, args=[], kwds={}):
        """
        EXAMPLES:
            sage: lisp.function_call('sin', ['2'])
            0.9092974
            sage: lisp.sin(2)
            0.9092974
        """
        if function == '':
            raise ValueError, "function name must be nonempty"
        if function[:2] == "__":
            raise AttributeError
        if not isinstance(args, list):
            args = [args]
        for i in range(len(args)):
            if not isinstance(args[i], LispElement):
                args[i] = self.new(args[i])
        for key, value in kwds.items():
            if not isinstance(args[i], LispElement):
                kwds[key] = self.new(value)
        return self.new("(%s %s)"%(function, ",".join([s.name() for s in args])))

class LispElement(ExpectElement):
    def __cmp__(self, other):
        """
        EXAMPLES:
            sage: one = lisp(1); two = lisp(2)
            sage: one == one
            True
            sage: one != two
            True
            sage: one < two
            True
            sage: two > one
            True
            sage: one < 1
            False
            sage: two == 2
            True

        """
        P = self._check_valid()
        if not hasattr(other, 'parent') or P is not other.parent():
            other = P(other)

        if P.eval('(= %s %s)'%(self.name(), other.name())) == P._true_symbol():
            return 0
        elif P.eval('(< %s %s)'%(self.name(), other.name())) == P._true_symbol():
            return -1
        else:
            return 1

    def bool(self):
        """
        EXAMPLES:
            sage: lisp(2).bool()
            True
            sage: lisp(0).bool()
            False
            sage: bool(lisp(2))
            True
        """
        return self != 0

    def _add_(self, right):
        """
        EXAMPLES:
            sage: a = lisp(1); b = lisp(2)
            sage: a + b
            3
        """
        P = self._check_valid()
        return P.new('(+ %s %s)'%(self._name, right._name))

    def _sub_(self, right):
        """
        EXAMPLES:
            sage: a = lisp(1); b = lisp(2)
            sage: a - b
            -1
        """
        P = self._check_valid()
        return P.new('(- %s %s)'%(self._name, right._name))

    def _mul_(self, right):
        """
        EXAMPLES:
            sage: a = lisp(1); b = lisp(2)
            sage: a * b
            2
        """
        P = self._check_valid()
        return P.new('(* %s %s)'%(self._name, right._name))

    def _div_(self, right):
        """
        EXAMPLES:
            sage: a = lisp(1); b = lisp(2)
            sage: a / b
            1/2
        """
        P = self._check_valid()
        return P.new('(/ %s %s)'%(self._name, right._name))

    def __pow__(self, n):
        """
        EXAMPLES:
            sage: a = lisp(3)
            sage: a^3
            27
        """
        return RingElement.__pow__(self, n)

class LispFunctionElement(FunctionElement):
    def _sage_doc_(self):
        """
        EXAMPLES:
            sage: two = lisp(2)
            sage: two.sin._sage_doc_()
            Traceback (most recent call last):
            ...
            NotImplementedError
        """
        M = self._obj.parent()
        return M.help(self._name)


class LispFunction(ExpectFunction):
    def _sage_doc_(self):
        """
        EXAMPLES:
            sage: lisp.sin._sage_doc_()
            Traceback (most recent call last):
            ...
            NotImplementedError
        """
        M = self._parent
        return M.help(self._name)



def is_LispElement(x):
    """
    EXAMPLES:
        sage: from sage.interfaces.lisp import is_LispElement
        sage: is_LispElement(lisp(2))
        True
        sage: is_LispElement(2)
        False
    """
    return isinstance(x, LispElement)

# An instance
lisp = Lisp()

def reduce_load_Lisp():
    """
    EXAMPLES:
        sage: from sage.interfaces.lisp import reduce_load_Lisp
        sage: reduce_load_Lisp()
        Lisp Interpreter
    """
    return lisp

import os
def lisp_console():
    """
    Spawn a new Lisp command-line session.

    EXAMPLES:
        sage: lisp_console() #not tested
          i i i i i i i       ooooo    o        ooooooo   ooooo   ooooo
          I I I I I I I      8     8   8           8     8     o  8    8
          I  \ `+' /  I      8         8           8     8        8    8
           \  `-+-'  /       8         8           8      ooooo   8oooo
            `-__|__-'        8         8           8           8  8
                |            8     o   8           8     o     8  8
          ------+------       ooooo    8oooooo  ooo8ooo   ooooo   8
        ...
    """
    os.system('clisp')


