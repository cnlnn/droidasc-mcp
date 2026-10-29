# This file is part of Androguard.
#
# Copyright (C) 2012, Geoffroy Gueguen <geoffroy.gueguen@gmail.com>
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from struct import pack, unpack


import dadguard.decompiler.util as util
from dadguard.decompiler.instruction import (
    ArrayLengthExpression,
    ArrayLoadExpression,
    ArrayStoreInstruction,
    AssignExpression,
    BaseClass,
    BinaryCompExpression,
    BinaryExpression,
    BinaryExpression2Addr,
    BinaryExpressionLit,
    CastExpression,
    CheckCastExpression,
    ConditionalExpression,
    ConditionalZExpression,
    Constant,
    FillArrayExpression,
    FilledArrayExpression,
    InstanceExpression,
    InstanceInstruction,
    InvokeDirectInstruction,
    InvokeInstruction,
    InvokeRangeInstruction,
    InvokeStaticInstruction,
    MonitorEnterExpression,
    MonitorExitExpression,
    MoveExceptionExpression,
    MoveExpression,
    MoveResultExpression,
    NewArrayExpression,
    NewInstance,
    NopExpression,
    ReturnInstruction,
    StaticExpression,
    StaticInstruction,
    SwitchExpression,
    ThisParam,
    ThrowExpression,
    UnaryExpression,
    Variable,
)


class Op:
    CMP = 'cmp'
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    MOD = '%'
    AND = '&'
    OR = '|'
    XOR = '^'
    EQUAL = '=='
    NEQUAL = '!='
    GREATER = '>'
    LOWER = '<'
    GEQUAL = '>='
    LEQUAL = '<='
    NEG = '-'
    NOT = '~'
    INTSHL = '<<'  # '(%s << ( %s & 0x1f ))'
    INTSHR = '>>'  # '(%s >> ( %s & 0x1f ))'
    LONGSHL = '<<'  # '(%s << ( %s & 0x3f ))'
    LONGSHR = '>>'  # '(%s >> ( %s & 0x3f ))'


def get_variables(vmap, *variables):
    res = []
    for variable in variables:
        res.append(vmap.setdefault(variable, Variable(variable)))
    if len(res) == 1:
        return res[0]
    return res


def assign_const(dest_reg, cst, vmap):
    return AssignExpression(get_variables(vmap, dest_reg), cst)


def assign_cmp(val_a, val_b, val_c, cmp_type, vmap):
    reg_a, reg_b, reg_c = get_variables(vmap, val_a, val_b, val_c)
    exp = BinaryCompExpression(Op.CMP, reg_b, reg_c, cmp_type)
    return AssignExpression(reg_a, exp)


def load_array_exp(val_a, val_b, val_c, ar_type, vmap):
    reg_a, reg_b, reg_c = get_variables(vmap, val_a, val_b, val_c)
    return AssignExpression(reg_a, ArrayLoadExpression(reg_b, reg_c, ar_type))


def store_array_inst(val_a, val_b, val_c, ar_type, vmap):
    reg_a, reg_b, reg_c = get_variables(vmap, val_a, val_b, val_c)
    return ArrayStoreInstruction(reg_a, reg_b, reg_c, ar_type)


def assign_cast_exp(val_a, val_b, val_op, op_type, vmap):
    reg_a, reg_b = get_variables(vmap, val_a, val_b)
    return AssignExpression(reg_a, CastExpression(val_op, op_type, reg_b))


def assign_binary_exp(ins, val_op, op_type, vmap):
    reg_a, reg_b, reg_c = get_variables(vmap, ins.AA, ins.BB, ins.CC)
    return AssignExpression(
        reg_a, BinaryExpression(val_op, reg_b, reg_c, op_type)
    )


def assign_binary_2addr_exp(ins, val_op, op_type, vmap):
    reg_a, reg_b = get_variables(vmap, ins.A, ins.B)
    return AssignExpression(
        reg_a, BinaryExpression2Addr(val_op, reg_a, reg_b, op_type)
    )


def assign_lit(op_type, val_cst, val_a, val_b, vmap):
    cst = Constant(val_cst, 'I')
    var_a, var_b = get_variables(vmap, val_a, val_b)
    return AssignExpression(var_a, BinaryExpressionLit(op_type, var_b, cst))


## From here on, there are all defined instructions


# nop
def nop(ins, vmap):
    return NopExpression()


# move vA, vB ( 4b, 4b )
def move(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.A, ins.B)
    return MoveExpression(reg_a, reg_b)


# move/from16 vAA, vBBBB ( 8b, 16b )
def movefrom16(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.AA, ins.BBBB)
    return MoveExpression(reg_a, reg_b)


# move/16 vAAAA, vBBBB ( 16b, 16b )
def move16(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.AAAA, ins.BBBB)
    return MoveExpression(reg_a, reg_b)


# move-wide vA, vB ( 4b, 4b )
def movewide(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.A, ins.B)
    return MoveExpression(reg_a, reg_b)


# move-wide/from16 vAA, vBBBB ( 8b, 16b )
def movewidefrom16(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.AA, ins.BBBB)
    return MoveExpression(reg_a, reg_b)


# move-wide/16 vAAAA, vBBBB ( 16b, 16b )
def movewide16(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.AAAA, ins.BBBB)
    return MoveExpression(reg_a, reg_b)


# move-object vA, vB ( 4b, 4b )
def moveobject(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.A, ins.B)
    return MoveExpression(reg_a, reg_b)


# move-object/from16 vAA, vBBBB ( 8b, 16b )
def moveobjectfrom16(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.AA, ins.BBBB)
    return MoveExpression(reg_a, reg_b)


# move-object/16 vAAAA, vBBBB ( 16b, 16b )
def moveobject16(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.AAAA, ins.BBBB)
    return MoveExpression(reg_a, reg_b)


# move-result vAA ( 8b )
def moveresult(ins, vmap, ret):
    return MoveResultExpression(get_variables(vmap, ins.AA), ret)


# move-result-wide vAA ( 8b )
def moveresultwide(ins, vmap, ret):
    return MoveResultExpression(get_variables(vmap, ins.AA), ret)


# move-result-object vAA ( 8b )
def moveresultobject(ins, vmap, ret):
    return MoveResultExpression(get_variables(vmap, ins.AA), ret)


# move-exception vAA ( 8b )
def moveexception(ins, vmap, _type):
    return MoveExceptionExpression(get_variables(vmap, ins.AA), _type)


# return-void
def returnvoid(ins, vmap):
    return ReturnInstruction(None)


# return vAA ( 8b )
def return_reg(ins, vmap):
    return ReturnInstruction(get_variables(vmap, ins.AA))


# return-wide vAA ( 8b )
def returnwide(ins, vmap):
    return ReturnInstruction(get_variables(vmap, ins.AA))


# return-object vAA ( 8b )
def returnobject(ins, vmap):
    return ReturnInstruction(get_variables(vmap, ins.AA))


# const/4 vA, #+B ( 4b, 4b )
def const4(ins, vmap):
    cst = Constant(ins.B, 'I')
    return assign_const(ins.A, cst, vmap)


# const/16 vAA, #+BBBB ( 8b, 16b )
def const16(ins, vmap):
    cst = Constant(ins.BBBB, 'I')
    return assign_const(ins.AA, cst, vmap)


# const vAA, #+BBBBBBBB ( 8b, 32b )
def const(ins, vmap):
    cst = Constant(ins.BBBBBBBB, 'I')
    return assign_const(ins.AA, cst, vmap)


# const/high16 vAA, #+BBBB0000 ( 8b, 16b )
def consthigh16(ins, vmap):
    cst = Constant(ins.BBBB, 'I')
    return assign_const(ins.AA, cst, vmap)


# const-wide/16 vAA, #+BBBB ( 8b, 16b )
def constwide16(ins, vmap):
    cst = Constant(ins.BBBB, 'J')
    return assign_const(ins.AA, cst, vmap)


# const-wide/32 vAA, #+BBBBBBBB ( 8b, 32b )
def constwide32(ins, vmap):
    cst = Constant(ins.BBBBBBBB, 'J')
    return assign_const(ins.AA, cst, vmap)


# const-wide vAA, #+BBBBBBBBBBBBBBBB ( 8b, 64b )
def constwide(ins, vmap):
    cst = Constant(ins.BBBBBBBBBBBBBBBB, 'J')
    return assign_const(ins.AA, cst, vmap)


# const-wide/high16 vAA, #+BBBB000000000000 ( 8b, 16b )
def constwidehigh16(ins, vmap):
    cst = Constant(ins.BBBB, 'J')
    return assign_const(ins.AA, cst, vmap)


# const-string vAA ( 8b )
def conststring(ins, vmap):
    cst = Constant(ins.get_raw_string(), 'Ljava/lang/String;')
    return assign_const(ins.AA, cst, vmap)


# const-string/jumbo vAA ( 8b )
def conststringjumbo(ins, vmap):
    cst = Constant(ins.get_raw_string(), 'Ljava/lang/String;')
    return assign_const(ins.AA, cst, vmap)


# const-class vAA, type@BBBB ( 8b )
def constclass(ins, vmap):
    cst = Constant(
        util.get_type(ins.get_string()),
        'Ljava/lang/Class;',
        descriptor=ins.get_string(),
    )
    return assign_const(ins.AA, cst, vmap)


# monitor-enter vAA ( 8b )
def monitorenter(ins, vmap):
    return MonitorEnterExpression(get_variables(vmap, ins.AA))


# monitor-exit vAA ( 8b )
def monitorexit(ins, vmap):
    a = get_variables(vmap, ins.AA)
    return MonitorExitExpression(a)


# check-cast vAA ( 8b )
def checkcast(ins, vmap):
    cast_type = util.get_type(ins.get_translated_kind())
    cast_var = get_variables(vmap, ins.AA)
    cast_expr = CheckCastExpression(
        cast_var, cast_type, descriptor=ins.get_translated_kind()
    )
    return AssignExpression(cast_var, cast_expr)


# instance-of vA, vB ( 4b, 4b )
def instanceof(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.A, ins.B)
    reg_c = BaseClass(
        util.get_type(ins.get_translated_kind()),
        descriptor=ins.get_translated_kind(),
    )
    exp = BinaryExpression('instanceof', reg_b, reg_c, 'Z')
    return AssignExpression(reg_a, exp)


# array-length vA, vB ( 4b, 4b )
def arraylength(ins, vmap):
    reg_a, reg_b = get_variables(vmap, ins.A, ins.B)
    return AssignExpression(reg_a, ArrayLengthExpression(reg_b))


# new-instance vAA ( 8b )
def newinstance(ins, vmap):
    reg_a = get_variables(vmap, ins.AA)
    ins_type = ins.cm.get_type(ins.BBBB)
    return AssignExpression(reg_a, NewInstance(ins_type))


# new-array vA, vB ( 8b, size )
def newarray(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = NewArrayExpression(b, ins.cm.get_type(ins.CCCC))
    return AssignExpression(a, exp)


# filled-new-array {vD, vE, vF, vG, vA} ( 4b each )
def fillednewarray(ins, vmap, ret):
    c, d, e, f, g = get_variables(vmap, ins.C, ins.D, ins.E, ins.F, ins.G)
    array_type = ins.cm.get_type(ins.BBBB)
    exp = FilledArrayExpression(ins.A, array_type, [c, d, e, f, g][: ins.A])
    return AssignExpression(ret, exp)


# filled-new-array/range {vCCCC..vNNNN} ( 16b )
def fillednewarrayrange(ins, vmap, ret):
    a, c, n = get_variables(vmap, ins.AA, ins.CCCC, ins.NNNN)
    array_type = ins.cm.get_type(ins.BBBB)
    exp = FilledArrayExpression(a, array_type, [c, n])
    return AssignExpression(ret, exp)


# fill-array-data vAA, +BBBBBBBB ( 8b, 32b )
def fillarraydata(ins, vmap, value):
    return FillArrayExpression(get_variables(vmap, ins.AA), value)


# fill-array-data-payload vAA, +BBBBBBBB ( 8b, 32b )
def fillarraydatapayload(ins, vmap):
    return FillArrayExpression(None)


# throw vAA ( 8b )
def throw(ins, vmap):
    return ThrowExpression(get_variables(vmap, ins.AA))


# goto +AA ( 8b )
def goto(ins, vmap):
    return NopExpression()


# goto/16 +AAAA ( 16b )
def goto16(ins, vmap):
    return NopExpression()


# goto/32 +AAAAAAAA ( 32b )
def goto32(ins, vmap):
    return NopExpression()


# packed-switch vAA, +BBBBBBBB ( reg to test, 32b )
def packedswitch(ins, vmap):
    reg_a = get_variables(vmap, ins.AA)
    return SwitchExpression(reg_a, ins.BBBBBBBB)


# sparse-switch vAA, +BBBBBBBB ( reg to test, 32b )
def sparseswitch(ins, vmap):
    reg_a = get_variables(vmap, ins.AA)
    return SwitchExpression(reg_a, ins.BBBBBBBB)


# cmpl-float vAA, vBB, vCC ( 8b, 8b, 8b )
def cmplfloat(ins, vmap):
    return assign_cmp(ins.AA, ins.BB, ins.CC, 'F', vmap)


# cmpg-float vAA, vBB, vCC ( 8b, 8b, 8b )
def cmpgfloat(ins, vmap):
    return assign_cmp(ins.AA, ins.BB, ins.CC, 'F', vmap)


# cmpl-double vAA, vBB, vCC ( 8b, 8b, 8b )
def cmpldouble(ins, vmap):
    return assign_cmp(ins.AA, ins.BB, ins.CC, 'D', vmap)


# cmpg-double vAA, vBB, vCC ( 8b, 8b, 8b )
def cmpgdouble(ins, vmap):
    return assign_cmp(ins.AA, ins.BB, ins.CC, 'D', vmap)


# cmp-long vAA, vBB, vCC ( 8b, 8b, 8b )
def cmplong(ins, vmap):
    return assign_cmp(ins.AA, ins.BB, ins.CC, 'J', vmap)


# if-eq vA, vB, +CCCC ( 4b, 4b, 16b )
def ifeq(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    return ConditionalExpression(Op.EQUAL, a, b)


# if-ne vA, vB, +CCCC ( 4b, 4b, 16b )
def ifne(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    return ConditionalExpression(Op.NEQUAL, a, b)


# if-lt vA, vB, +CCCC ( 4b, 4b, 16b )
def iflt(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    return ConditionalExpression(Op.LOWER, a, b)


# if-ge vA, vB, +CCCC ( 4b, 4b, 16b )
def ifge(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    return ConditionalExpression(Op.GEQUAL, a, b)


# if-gt vA, vB, +CCCC ( 4b, 4b, 16b )
def ifgt(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    return ConditionalExpression(Op.GREATER, a, b)


# if-le vA, vB, +CCCC ( 4b, 4b, 16b )
def ifle(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    return ConditionalExpression(Op.LEQUAL, a, b)


# if-eqz vAA, +BBBB ( 8b, 16b )
def ifeqz(ins, vmap):
    return ConditionalZExpression(Op.EQUAL, get_variables(vmap, ins.AA))


# if-nez vAA, +BBBB ( 8b, 16b )
def ifnez(ins, vmap):
    return ConditionalZExpression(Op.NEQUAL, get_variables(vmap, ins.AA))


# if-ltz vAA, +BBBB ( 8b, 16b )
def ifltz(ins, vmap):
    return ConditionalZExpression(Op.LOWER, get_variables(vmap, ins.AA))


# if-gez vAA, +BBBB ( 8b, 16b )
def ifgez(ins, vmap):
    return ConditionalZExpression(Op.GEQUAL, get_variables(vmap, ins.AA))


# if-gtz vAA, +BBBB ( 8b, 16b )
def ifgtz(ins, vmap):
    return ConditionalZExpression(Op.GREATER, get_variables(vmap, ins.AA))


# if-lez vAA, +BBBB (8b, 16b )
def iflez(ins, vmap):
    return ConditionalZExpression(Op.LEQUAL, get_variables(vmap, ins.AA))


# TODO: check type for all aget
# aget vAA, vBB, vCC ( 8b, 8b, 8b )
def aget(ins, vmap):
    return load_array_exp(ins.AA, ins.BB, ins.CC, None, vmap)


# aget-wide vAA, vBB, vCC ( 8b, 8b, 8b )
def agetwide(ins, vmap):
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'W', vmap)


# aget-object vAA, vBB, vCC ( 8b, 8b, 8b )
def agetobject(ins, vmap):
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'O', vmap)


# aget-boolean vAA, vBB, vCC ( 8b, 8b, 8b )
def agetboolean(ins, vmap):
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'Z', vmap)


# aget-byte vAA, vBB, vCC ( 8b, 8b, 8b )
def agetbyte(ins, vmap):
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'B', vmap)


# aget-char vAA, vBB, vCC ( 8b, 8b, 8b )
def agetchar(ins, vmap):
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'C', vmap)


# aget-short vAA, vBB, vCC ( 8b, 8b, 8b )
def agetshort(ins, vmap):
    return load_array_exp(ins.AA, ins.BB, ins.CC, 'S', vmap)


# aput vAA, vBB, vCC
def aput(ins, vmap):
    return store_array_inst(ins.AA, ins.BB, ins.CC, None, vmap)


# aput-wide vAA, vBB, vCC ( 8b, 8b, 8b )
def aputwide(ins, vmap):
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'W', vmap)


# aput-object vAA, vBB, vCC ( 8b, 8b, 8b )
def aputobject(ins, vmap):
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'O', vmap)


# aput-boolean vAA, vBB, vCC ( 8b, 8b, 8b )
def aputboolean(ins, vmap):
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'Z', vmap)


# aput-byte vAA, vBB, vCC ( 8b, 8b, 8b )
def aputbyte(ins, vmap):
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'B', vmap)


# aput-char vAA, vBB, vCC ( 8b, 8b, 8b )
def aputchar(ins, vmap):
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'C', vmap)


# aput-short vAA, vBB, vCC ( 8b, 8b, 8b )
def aputshort(ins, vmap):
    return store_array_inst(ins.AA, ins.BB, ins.CC, 'S', vmap)


# iget vA, vB ( 4b, 4b )
def iget(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = InstanceExpression(b, klass, ftype, name)
    return AssignExpression(a, exp)


# iget-wide vA, vB ( 4b, 4b )
def igetwide(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = InstanceExpression(b, klass, ftype, name)
    return AssignExpression(a, exp)


# iget-object vA, vB ( 4b, 4b )
def igetobject(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = InstanceExpression(b, klass, ftype, name)
    return AssignExpression(a, exp)


# iget-boolean vA, vB ( 4b, 4b )
def igetboolean(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = InstanceExpression(b, klass, ftype, name)
    return AssignExpression(a, exp)


# iget-byte vA, vB ( 4b, 4b )
def igetbyte(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = InstanceExpression(b, klass, ftype, name)
    return AssignExpression(a, exp)


# iget-char vA, vB ( 4b, 4b )
def igetchar(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = InstanceExpression(b, klass, ftype, name)
    return AssignExpression(a, exp)


# iget-short vA, vB ( 4b, 4b )
def igetshort(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = InstanceExpression(b, klass, ftype, name)
    return AssignExpression(a, exp)


# iput vA, vB ( 4b, 4b )
def iput(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    return InstanceInstruction(a, b, klass, atype, name)


# iput-wide vA, vB ( 4b, 4b )
def iputwide(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    return InstanceInstruction(a, b, klass, atype, name)


# iput-object vA, vB ( 4b, 4b )
def iputobject(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    return InstanceInstruction(a, b, klass, atype, name)


# iput-boolean vA, vB ( 4b, 4b )
def iputboolean(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    return InstanceInstruction(a, b, klass, atype, name)


# iput-byte vA, vB ( 4b, 4b )
def iputbyte(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    return InstanceInstruction(a, b, klass, atype, name)


# iput-char vA, vB ( 4b, 4b )
def iputchar(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    return InstanceInstruction(a, b, klass, atype, name)


# iput-short vA, vB ( 4b, 4b )
def iputshort(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.CCCC)
    a, b = get_variables(vmap, ins.A, ins.B)
    return InstanceInstruction(a, b, klass, atype, name)


# sget vAA ( 8b )
def sget(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.BBBB)
    exp = StaticExpression(klass, atype, name)
    a = get_variables(vmap, ins.AA)
    return AssignExpression(a, exp)


# sget-wide vAA ( 8b )
def sgetwide(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.BBBB)
    exp = StaticExpression(klass, atype, name)
    a = get_variables(vmap, ins.AA)
    return AssignExpression(a, exp)


# sget-object vAA ( 8b )
def sgetobject(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.BBBB)
    exp = StaticExpression(klass, atype, name)
    a = get_variables(vmap, ins.AA)
    return AssignExpression(a, exp)


# sget-boolean vAA ( 8b )
def sgetboolean(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.BBBB)
    exp = StaticExpression(klass, atype, name)
    a = get_variables(vmap, ins.AA)
    return AssignExpression(a, exp)


# sget-byte vAA ( 8b )
def sgetbyte(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.BBBB)
    exp = StaticExpression(klass, atype, name)
    a = get_variables(vmap, ins.AA)
    return AssignExpression(a, exp)


# sget-char vAA ( 8b )
def sgetchar(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.BBBB)
    exp = StaticExpression(klass, atype, name)
    a = get_variables(vmap, ins.AA)
    return AssignExpression(a, exp)


# sget-short vAA ( 8b )
def sgetshort(ins, vmap):
    klass, atype, name = ins.cm.get_field(ins.BBBB)
    exp = StaticExpression(klass, atype, name)
    a = get_variables(vmap, ins.AA)
    return AssignExpression(a, exp)


# sput vAA ( 8b )
def sput(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.BBBB)
    a = get_variables(vmap, ins.AA)
    return StaticInstruction(a, klass, ftype, name)


# sput-wide vAA ( 8b )
def sputwide(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.BBBB)
    a = get_variables(vmap, ins.AA)
    return StaticInstruction(a, klass, ftype, name)


# sput-object vAA ( 8b )
def sputobject(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.BBBB)
    a = get_variables(vmap, ins.AA)
    return StaticInstruction(a, klass, ftype, name)


# sput-boolean vAA ( 8b )
def sputboolean(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.BBBB)
    a = get_variables(vmap, ins.AA)
    return StaticInstruction(a, klass, ftype, name)


# sput-wide vAA ( 8b )
def sputbyte(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.BBBB)
    a = get_variables(vmap, ins.AA)
    return StaticInstruction(a, klass, ftype, name)


# sput-char vAA ( 8b )
def sputchar(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.BBBB)
    a = get_variables(vmap, ins.AA)
    return StaticInstruction(a, klass, ftype, name)


# sput-short vAA ( 8b )
def sputshort(ins, vmap):
    klass, ftype, name = ins.cm.get_field(ins.BBBB)
    a = get_variables(vmap, ins.AA)
    return StaticInstruction(a, klass, ftype, name)


def get_args(vmap, param_type, largs):
    num_param = 0
    args = []
    if len(param_type) > len(largs):
        return args
    for type_ in param_type:
        param = largs[num_param]
        args.append(param)
        num_param += util.get_type_size(type_)

    if len(param_type) == 1:
        return [get_variables(vmap, *args)]
    return get_variables(vmap, *args)


# invoke-virtual {vD, vE, vF, vG, vA} ( 4b each )
def invokevirtual(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = [ins.D, ins.E, ins.F, ins.G]
    args = get_args(vmap, param_type, largs)
    c = get_variables(vmap, ins.C)
    returned = None if ret_type == 'V' else ret.new()
    exp = InvokeInstruction(
        cls_name, name, c, ret_type, param_type, args, method.get_triple()
    )
    return AssignExpression(returned, exp)


# invoke-super {vD, vE, vF, vG, vA} ( 4b each )
def invokesuper(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = [ins.D, ins.E, ins.F, ins.G]
    args = get_args(vmap, param_type, largs)
    superclass = BaseClass('super')
    returned = None if ret_type == 'V' else ret.new()
    exp = InvokeInstruction(
        cls_name,
        name,
        superclass,
        ret_type,
        param_type,
        args,
        method.get_triple(),
    )
    return AssignExpression(returned, exp)


# invoke-direct {vD, vE, vF, vG, vA} ( 4b each )
def invokedirect(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = [ins.D, ins.E, ins.F, ins.G]
    args = get_args(vmap, param_type, largs)
    base = get_variables(vmap, ins.C)
    if ret_type == 'V':
        if isinstance(base, ThisParam):
            returned = None
        else:
            returned = base
            ret.set_to(base)
    else:
        returned = ret.new()
    exp = InvokeDirectInstruction(
        cls_name, name, base, ret_type, param_type, args, method.get_triple()
    )
    return AssignExpression(returned, exp)


# invoke-static {vD, vE, vF, vG, vA} ( 4b each )
def invokestatic(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = [ins.C, ins.D, ins.E, ins.F, ins.G]
    args = get_args(vmap, param_type, largs)
    base = BaseClass(cls_name, descriptor=method.get_class_name())
    returned = None if ret_type == 'V' else ret.new()
    exp = InvokeStaticInstruction(
        cls_name, name, base, ret_type, param_type, args, method.get_triple()
    )
    return AssignExpression(returned, exp)


# invoke-interface {vD, vE, vF, vG, vA} ( 4b each )
def invokeinterface(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = [ins.D, ins.E, ins.F, ins.G]
    args = get_args(vmap, param_type, largs)
    c = get_variables(vmap, ins.C)
    returned = None if ret_type == 'V' else ret.new()
    exp = InvokeInstruction(
        cls_name, name, c, ret_type, param_type, args, method.get_triple()
    )
    return AssignExpression(returned, exp)


# invoke-virtual/range {vCCCC..vNNNN} ( 16b each )
def invokevirtualrange(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = list(range(ins.CCCC, ins.NNNN + 1))
    this_arg = get_variables(vmap, largs[0])
    args = get_args(vmap, param_type, largs[1:])
    returned = None if ret_type == 'V' else ret.new()
    exp = InvokeRangeInstruction(
        cls_name,
        name,
        ret_type,
        param_type,
        [this_arg] + args,
        method.get_triple(),
    )
    return AssignExpression(returned, exp)


# invoke-super/range {vCCCC..vNNNN} ( 16b each )
def invokesuperrange(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = list(range(ins.CCCC, ins.NNNN + 1))
    args = get_args(vmap, param_type, largs[1:])
    base = get_variables(vmap, ins.CCCC)
    if ret_type != 'V':
        returned = ret.new()
    else:
        returned = base
        ret.set_to(base)
    superclass = BaseClass('super')
    exp = InvokeRangeInstruction(
        cls_name,
        name,
        ret_type,
        param_type,
        [superclass] + args,
        method.get_triple(),
    )
    return AssignExpression(returned, exp)


# invoke-direct/range {vCCCC..vNNNN} ( 16b each )
def invokedirectrange(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = list(range(ins.CCCC, ins.NNNN + 1))
    this_arg = get_variables(vmap, largs[0])
    args = get_args(vmap, param_type, largs[1:])
    base = get_variables(vmap, ins.CCCC)
    if ret_type != 'V':
        returned = ret.new()
    else:
        returned = base
        ret.set_to(base)
    exp = InvokeRangeInstruction(
        cls_name,
        name,
        ret_type,
        param_type,
        [this_arg] + args,
        method.get_triple(),
    )
    return AssignExpression(returned, exp)


# invoke-static/range {vCCCC..vNNNN} ( 16b each )
def invokestaticrange(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = list(range(ins.CCCC, ins.NNNN + 1))
    args = get_args(vmap, param_type, largs)
    base = BaseClass(cls_name, descriptor=method.get_class_name())
    returned = None if ret_type == 'V' else ret.new()
    exp = InvokeStaticInstruction(
        cls_name, name, base, ret_type, param_type, args, method.get_triple()
    )
    return AssignExpression(returned, exp)


# invoke-interface/range {vCCCC..vNNNN} ( 16b each )
def invokeinterfacerange(ins, vmap, ret):
    method = ins.cm.get_method_ref(ins.BBBB)
    cls_name = util.get_type(method.get_class_name())
    name = method.get_name()
    param_type, ret_type = method.get_proto()
    param_type = util.get_params_type(param_type)
    largs = list(range(ins.CCCC, ins.NNNN + 1))
    base_arg = get_variables(vmap, largs[0])
    args = get_args(vmap, param_type, largs[1:])
    returned = None if ret_type == 'V' else ret.new()
    exp = InvokeRangeInstruction(
        cls_name,
        name,
        ret_type,
        param_type,
        [base_arg] + args,
        method.get_triple(),
    )
    return AssignExpression(returned, exp)


# neg-int vA, vB ( 4b, 4b )
def negint(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = UnaryExpression(Op.NEG, b, 'I')
    return AssignExpression(a, exp)


# not-int vA, vB ( 4b, 4b )
def notint(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = UnaryExpression(Op.NOT, b, 'I')
    return AssignExpression(a, exp)


# neg-long vA, vB ( 4b, 4b )
def neglong(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = UnaryExpression(Op.NEG, b, 'J')
    return AssignExpression(a, exp)


# not-long vA, vB ( 4b, 4b )
def notlong(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = UnaryExpression(Op.NOT, b, 'J')
    return AssignExpression(a, exp)


# neg-float vA, vB ( 4b, 4b )
def negfloat(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = UnaryExpression(Op.NEG, b, 'F')
    return AssignExpression(a, exp)


# neg-double vA, vB ( 4b, 4b )
def negdouble(ins, vmap):
    a, b = get_variables(vmap, ins.A, ins.B)
    exp = UnaryExpression(Op.NEG, b, 'D')
    return AssignExpression(a, exp)


# int-to-long vA, vB ( 4b, 4b )
def inttolong(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(long)', 'J', vmap)


# int-to-float vA, vB ( 4b, 4b )
def inttofloat(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(float)', 'F', vmap)


# int-to-double vA, vB ( 4b, 4b )
def inttodouble(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(double)', 'D', vmap)


# long-to-int vA, vB ( 4b, 4b )
def longtoint(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(int)', 'I', vmap)


# long-to-float vA, vB ( 4b, 4b )
def longtofloat(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(float)', 'F', vmap)


# long-to-double vA, vB ( 4b, 4b )
def longtodouble(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(double)', 'D', vmap)


# float-to-int vA, vB ( 4b, 4b )
def floattoint(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(int)', 'I', vmap)


# float-to-long vA, vB ( 4b, 4b )
def floattolong(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(long)', 'J', vmap)


# float-to-double vA, vB ( 4b, 4b )
def floattodouble(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(double)', 'D', vmap)


# double-to-int vA, vB ( 4b, 4b )
def doubletoint(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(int)', 'I', vmap)


# double-to-long vA, vB ( 4b, 4b )
def doubletolong(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(long)', 'J', vmap)


# double-to-float vA, vB ( 4b, 4b )
def doubletofloat(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(float)', 'F', vmap)


# int-to-byte vA, vB ( 4b, 4b )
def inttobyte(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(byte)', 'B', vmap)


# int-to-char vA, vB ( 4b, 4b )
def inttochar(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(char)', 'C', vmap)


# int-to-short vA, vB ( 4b, 4b )
def inttoshort(ins, vmap):
    return assign_cast_exp(ins.A, ins.B, '(short)', 'S', vmap)


# add-int vAA, vBB, vCC ( 8b, 8b, 8b )
def addint(ins, vmap):
    return assign_binary_exp(ins, Op.ADD, 'I', vmap)


# sub-int vAA, vBB, vCC ( 8b, 8b, 8b )
def subint(ins, vmap):
    return assign_binary_exp(ins, Op.SUB, 'I', vmap)


# mul-int vAA, vBB, vCC ( 8b, 8b, 8b )
def mulint(ins, vmap):
    return assign_binary_exp(ins, Op.MUL, 'I', vmap)


# div-int vAA, vBB, vCC ( 8b, 8b, 8b )
def divint(ins, vmap):
    return assign_binary_exp(ins, Op.DIV, 'I', vmap)


# rem-int vAA, vBB, vCC ( 8b, 8b, 8b )
def remint(ins, vmap):
    return assign_binary_exp(ins, Op.MOD, 'I', vmap)


# and-int vAA, vBB, vCC ( 8b, 8b, 8b )
def andint(ins, vmap):
    return assign_binary_exp(ins, Op.AND, 'I', vmap)


# or-int vAA, vBB, vCC ( 8b, 8b, 8b )
def orint(ins, vmap):
    return assign_binary_exp(ins, Op.OR, 'I', vmap)


# xor-int vAA, vBB, vCC ( 8b, 8b, 8b )
def xorint(ins, vmap):
    return assign_binary_exp(ins, Op.XOR, 'I', vmap)


# shl-int vAA, vBB, vCC ( 8b, 8b, 8b )
def shlint(ins, vmap):
    return assign_binary_exp(ins, Op.INTSHL, 'I', vmap)


# shr-int vAA, vBB, vCC ( 8b, 8b, 8b )
def shrint(ins, vmap):
    return assign_binary_exp(ins, Op.INTSHR, 'I', vmap)


# ushr-int vAA, vBB, vCC ( 8b, 8b, 8b )
def ushrint(ins, vmap):
    return assign_binary_exp(ins, Op.INTSHR, 'I', vmap)


# add-long vAA, vBB, vCC ( 8b, 8b, 8b )
def addlong(ins, vmap):
    return assign_binary_exp(ins, Op.ADD, 'J', vmap)


# sub-long vAA, vBB, vCC ( 8b, 8b, 8b )
def sublong(ins, vmap):
    return assign_binary_exp(ins, Op.SUB, 'J', vmap)


# mul-long vAA, vBB, vCC ( 8b, 8b, 8b )
def mullong(ins, vmap):
    return assign_binary_exp(ins, Op.MUL, 'J', vmap)


# div-long vAA, vBB, vCC ( 8b, 8b, 8b )
def divlong(ins, vmap):
    return assign_binary_exp(ins, Op.DIV, 'J', vmap)


# rem-long vAA, vBB, vCC ( 8b, 8b, 8b )
def remlong(ins, vmap):
    return assign_binary_exp(ins, Op.MOD, 'J', vmap)


# and-long vAA, vBB, vCC ( 8b, 8b, 8b )
def andlong(ins, vmap):
    return assign_binary_exp(ins, Op.AND, 'J', vmap)


# or-long vAA, vBB, vCC ( 8b, 8b, 8b )
def orlong(ins, vmap):
    return assign_binary_exp(ins, Op.OR, 'J', vmap)


# xor-long vAA, vBB, vCC ( 8b, 8b, 8b )
def xorlong(ins, vmap):
    return assign_binary_exp(ins, Op.XOR, 'J', vmap)


# shl-long vAA, vBB, vCC ( 8b, 8b, 8b )
def shllong(ins, vmap):
    return assign_binary_exp(ins, Op.LONGSHL, 'J', vmap)


# shr-long vAA, vBB, vCC ( 8b, 8b, 8b )
def shrlong(ins, vmap):
    return assign_binary_exp(ins, Op.LONGSHR, 'J', vmap)


# ushr-long vAA, vBB, vCC ( 8b, 8b, 8b )
def ushrlong(ins, vmap):
    return assign_binary_exp(ins, Op.LONGSHR, 'J', vmap)


# add-float vAA, vBB, vCC ( 8b, 8b, 8b )
def addfloat(ins, vmap):
    return assign_binary_exp(ins, Op.ADD, 'F', vmap)


# sub-float vAA, vBB, vCC ( 8b, 8b, 8b )
def subfloat(ins, vmap):
    return assign_binary_exp(ins, Op.SUB, 'F', vmap)


# mul-float vAA, vBB, vCC ( 8b, 8b, 8b )
def mulfloat(ins, vmap):
    return assign_binary_exp(ins, Op.MUL, 'F', vmap)


# div-float vAA, vBB, vCC ( 8b, 8b, 8b )
def divfloat(ins, vmap):
    return assign_binary_exp(ins, Op.DIV, 'F', vmap)


# rem-float vAA, vBB, vCC ( 8b, 8b, 8b )
def remfloat(ins, vmap):
    return assign_binary_exp(ins, Op.MOD, 'F', vmap)


# add-double vAA, vBB, vCC ( 8b, 8b, 8b )
def adddouble(ins, vmap):
    return assign_binary_exp(ins, Op.ADD, 'D', vmap)


# sub-double vAA, vBB, vCC ( 8b, 8b, 8b )
def subdouble(ins, vmap):
    return assign_binary_exp(ins, Op.SUB, 'D', vmap)


# mul-double vAA, vBB, vCC ( 8b, 8b, 8b )
def muldouble(ins, vmap):
    return assign_binary_exp(ins, Op.MUL, 'D', vmap)


# div-double vAA, vBB, vCC ( 8b, 8b, 8b )
def divdouble(ins, vmap):
    return assign_binary_exp(ins, Op.DIV, 'D', vmap)


# rem-double vAA, vBB, vCC ( 8b, 8b, 8b )
def remdouble(ins, vmap):
    return assign_binary_exp(ins, Op.MOD, 'D', vmap)


# add-int/2addr vA, vB ( 4b, 4b )
def addint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.ADD, 'I', vmap)


# sub-int/2addr vA, vB ( 4b, 4b )
def subint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.SUB, 'I', vmap)


# mul-int/2addr vA, vB ( 4b, 4b )
def mulint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.MUL, 'I', vmap)


# div-int/2addr vA, vB ( 4b, 4b )
def divint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.DIV, 'I', vmap)


# rem-int/2addr vA, vB ( 4b, 4b )
def remint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.MOD, 'I', vmap)


# and-int/2addr vA, vB ( 4b, 4b )
def andint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.AND, 'I', vmap)


# or-int/2addr vA, vB ( 4b, 4b )
def orint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.OR, 'I', vmap)


# xor-int/2addr vA, vB ( 4b, 4b )
def xorint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.XOR, 'I', vmap)


# shl-int/2addr vA, vB ( 4b, 4b )
def shlint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.INTSHL, 'I', vmap)


# shr-int/2addr vA, vB ( 4b, 4b )
def shrint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.INTSHR, 'I', vmap)


# ushr-int/2addr vA, vB ( 4b, 4b )
def ushrint2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.INTSHR, 'I', vmap)


# add-long/2addr vA, vB ( 4b, 4b )
def addlong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.ADD, 'J', vmap)


# sub-long/2addr vA, vB ( 4b, 4b )
def sublong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.SUB, 'J', vmap)


# mul-long/2addr vA, vB ( 4b, 4b )
def mullong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.MUL, 'J', vmap)


# div-long/2addr vA, vB ( 4b, 4b )
def divlong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.DIV, 'J', vmap)


# rem-long/2addr vA, vB ( 4b, 4b )
def remlong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.MOD, 'J', vmap)


# and-long/2addr vA, vB ( 4b, 4b )
def andlong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.AND, 'J', vmap)


# or-long/2addr vA, vB ( 4b, 4b )
def orlong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.OR, 'J', vmap)


# xor-long/2addr vA, vB ( 4b, 4b )
def xorlong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.XOR, 'J', vmap)


# shl-long/2addr vA, vB ( 4b, 4b )
def shllong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.LONGSHL, 'J', vmap)


# shr-long/2addr vA, vB ( 4b, 4b )
def shrlong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.LONGSHR, 'J', vmap)


# ushr-long/2addr vA, vB ( 4b, 4b )
def ushrlong2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.LONGSHR, 'J', vmap)


# add-float/2addr vA, vB ( 4b, 4b )
def addfloat2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.ADD, 'F', vmap)


# sub-float/2addr vA, vB ( 4b, 4b )
def subfloat2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.SUB, 'F', vmap)


# mul-float/2addr vA, vB ( 4b, 4b )
def mulfloat2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.MUL, 'F', vmap)


# div-float/2addr vA, vB ( 4b, 4b )
def divfloat2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.DIV, 'F', vmap)


# rem-float/2addr vA, vB ( 4b, 4b )
def remfloat2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.MOD, 'F', vmap)


# add-double/2addr vA, vB ( 4b, 4b )
def adddouble2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.ADD, 'D', vmap)


# sub-double/2addr vA, vB ( 4b, 4b )
def subdouble2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.SUB, 'D', vmap)


# mul-double/2addr vA, vB ( 4b, 4b )
def muldouble2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.MUL, 'D', vmap)


# div-double/2addr vA, vB ( 4b, 4b )
def divdouble2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.DIV, 'D', vmap)


# rem-double/2addr vA, vB ( 4b, 4b )
def remdouble2addr(ins, vmap):
    return assign_binary_2addr_exp(ins, Op.MOD, 'D', vmap)


# add-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def addintlit16(ins, vmap):
    return assign_lit(Op.ADD, ins.CCCC, ins.A, ins.B, vmap)


# rsub-int vA, vB, #+CCCC ( 4b, 4b, 16b )
def rsubint(ins, vmap):
    var_a, var_b = get_variables(vmap, ins.A, ins.B)
    cst = Constant(ins.CCCC, 'I')
    return AssignExpression(var_a, BinaryExpressionLit(Op.SUB, cst, var_b))


# mul-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def mulintlit16(ins, vmap):
    return assign_lit(Op.MUL, ins.CCCC, ins.A, ins.B, vmap)


# div-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def divintlit16(ins, vmap):
    return assign_lit(Op.DIV, ins.CCCC, ins.A, ins.B, vmap)


# rem-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def remintlit16(ins, vmap):
    return assign_lit(Op.MOD, ins.CCCC, ins.A, ins.B, vmap)


# and-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def andintlit16(ins, vmap):
    return assign_lit(Op.AND, ins.CCCC, ins.A, ins.B, vmap)


# or-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def orintlit16(ins, vmap):
    return assign_lit(Op.OR, ins.CCCC, ins.A, ins.B, vmap)


# xor-int/lit16 vA, vB, #+CCCC ( 4b, 4b, 16b )
def xorintlit16(ins, vmap):
    return assign_lit(Op.XOR, ins.CCCC, ins.A, ins.B, vmap)


# add-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def addintlit8(ins, vmap):
    literal, op = [(ins.CC, Op.ADD), (-ins.CC, Op.SUB)][ins.CC < 0]
    return assign_lit(op, literal, ins.AA, ins.BB, vmap)


# rsub-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def rsubintlit8(ins, vmap):
    var_a, var_b = get_variables(vmap, ins.AA, ins.BB)
    cst = Constant(ins.CC, 'I')
    return AssignExpression(var_a, BinaryExpressionLit(Op.SUB, cst, var_b))


# mul-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def mulintlit8(ins, vmap):
    return assign_lit(Op.MUL, ins.CC, ins.AA, ins.BB, vmap)


# div-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def divintlit8(ins, vmap):
    return assign_lit(Op.DIV, ins.CC, ins.AA, ins.BB, vmap)


# rem-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def remintlit8(ins, vmap):
    return assign_lit(Op.MOD, ins.CC, ins.AA, ins.BB, vmap)


# and-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def andintlit8(ins, vmap):
    return assign_lit(Op.AND, ins.CC, ins.AA, ins.BB, vmap)


# or-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def orintlit8(ins, vmap):
    return assign_lit(Op.OR, ins.CC, ins.AA, ins.BB, vmap)


# xor-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def xorintlit8(ins, vmap):
    return assign_lit(Op.XOR, ins.CC, ins.AA, ins.BB, vmap)


# shl-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def shlintlit8(ins, vmap):
    return assign_lit(Op.INTSHL, ins.CC, ins.AA, ins.BB, vmap)


# shr-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def shrintlit8(ins, vmap):
    return assign_lit(Op.INTSHR, ins.CC, ins.AA, ins.BB, vmap)


# ushr-int/lit8 vAA, vBB, #+CC ( 8b, 8b, 8b )
def ushrintlit8(ins, vmap):
    return assign_lit(Op.INTSHR, ins.CC, ins.AA, ins.BB, vmap)


# FIXME: Need to add all opcodes here, check for new unused ones.
# FIXME: The instruction set is dalvik version specific
INSTRUCTION_SET = [
    # 0x00
    nop,  # nop
    move,  # move
    movefrom16,  # move/from16
    move16,  # move/16
    movewide,  # move-wide
    movewidefrom16,  # move-wide/from16
    movewide16,  # move-wide/16
    moveobject,  # move-object
    moveobjectfrom16,  # move-object/from16
    moveobject16,  # move-object/16
    moveresult,  # move-result
    moveresultwide,  # move-result-wide
    moveresultobject,  # move-result-object
    moveexception,  # move-exception
    returnvoid,  # return-void
    return_reg,  # return
    # 0x10
    returnwide,  # return-wide
    returnobject,  # return-object
    const4,  # const/4
    const16,  # const/16
    const,  # const
    consthigh16,  # const/high16
    constwide16,  # const-wide/16
    constwide32,  # const-wide/32
    constwide,  # const-wide
    constwidehigh16,  # const-wide/high16
    conststring,  # const-string
    conststringjumbo,  # const-string/jumbo
    constclass,  # const-class
    monitorenter,  # monitor-enter
    monitorexit,  # monitor-exit
    checkcast,  # check-cast
    # 0x20
    instanceof,  # instance-of
    arraylength,  # array-length
    newinstance,  # new-instance
    newarray,  # new-array
    fillednewarray,  # filled-new-array
    fillednewarrayrange,  # filled-new-array/range
    fillarraydata,  # fill-array-data
    throw,  # throw
    goto,  # goto
    goto16,  # goto/16
    goto32,  # goto/32
    packedswitch,  # packed-switch
    sparseswitch,  # sparse-switch
    cmplfloat,  # cmpl-float
    cmpgfloat,  # cmpg-float
    cmpldouble,  # cmpl-double
    # 0x30
    cmpgdouble,  # cmpg-double
    cmplong,  # cmp-long
    ifeq,  # if-eq
    ifne,  # if-ne
    iflt,  # if-lt
    ifge,  # if-ge
    ifgt,  # if-gt
    ifle,  # if-le
    ifeqz,  # if-eqz
    ifnez,  # if-nez
    ifltz,  # if-ltz
    ifgez,  # if-gez
    ifgtz,  # if-gtz
    iflez,  # if-l
    nop,  # unused
    nop,  # unused
    # 0x40
    nop,  # unused
    nop,  # unused
    nop,  # unused
    nop,  # unused
    aget,  # aget
    agetwide,  # aget-wide
    agetobject,  # aget-object
    agetboolean,  # aget-boolean
    agetbyte,  # aget-byte
    agetchar,  # aget-char
    agetshort,  # aget-short
    aput,  # aput
    aputwide,  # aput-wide
    aputobject,  # aput-object
    aputboolean,  # aput-boolean
    aputbyte,  # aput-byte
    # 0x50
    aputchar,  # aput-char
    aputshort,  # aput-short
    iget,  # iget
    igetwide,  # iget-wide
    igetobject,  # iget-object
    igetboolean,  # iget-boolean
    igetbyte,  # iget-byte
    igetchar,  # iget-char
    igetshort,  # iget-short
    iput,  # iput
    iputwide,  # iput-wide
    iputobject,  # iput-object
    iputboolean,  # iput-boolean
    iputbyte,  # iput-byte
    iputchar,  # iput-char
    iputshort,  # iput-short
    # 0x60
    sget,  # sget
    sgetwide,  # sget-wide
    sgetobject,  # sget-object
    sgetboolean,  # sget-boolean
    sgetbyte,  # sget-byte
    sgetchar,  # sget-char
    sgetshort,  # sget-short
    sput,  # sput
    sputwide,  # sput-wide
    sputobject,  # sput-object
    sputboolean,  # sput-boolean
    sputbyte,  # sput-byte
    sputchar,  # sput-char
    sputshort,  # sput-short
    invokevirtual,  # invoke-virtual
    invokesuper,  # invoke-super
    # 0x70
    invokedirect,  # invoke-direct
    invokestatic,  # invoke-static
    invokeinterface,  # invoke-interface
    nop,  # unused
    invokevirtualrange,  # invoke-virtual/range
    invokesuperrange,  # invoke-super/range
    invokedirectrange,  # invoke-direct/range
    invokestaticrange,  # invoke-static/range
    invokeinterfacerange,  # invoke-interface/range
    nop,  # unused
    nop,  # unused
    negint,  # neg-int
    notint,  # not-int
    neglong,  # neg-long
    notlong,  # not-long
    negfloat,  # neg-float
    # 0x80
    negdouble,  # neg-double
    inttolong,  # int-to-long
    inttofloat,  # int-to-float
    inttodouble,  # int-to-double
    longtoint,  # long-to-int
    longtofloat,  # long-to-float
    longtodouble,  # long-to-double
    floattoint,  # float-to-int
    floattolong,  # float-to-long
    floattodouble,  # float-to-double
    doubletoint,  # double-to-int
    doubletolong,  # double-to-long
    doubletofloat,  # double-to-float
    inttobyte,  # int-to-byte
    inttochar,  # int-to-char
    inttoshort,  # int-to-short
    # 0x90
    addint,  # add-int
    subint,  # sub-int
    mulint,  # mul-int
    divint,  # div-int
    remint,  # rem-int
    andint,  # and-int
    orint,  # or-int
    xorint,  # xor-int
    shlint,  # shl-int
    shrint,  # shr-int
    ushrint,  # ushr-int
    addlong,  # add-long
    sublong,  # sub-long
    mullong,  # mul-long
    divlong,  # div-long
    remlong,  # rem-long
    # 0xa0
    andlong,  # and-long
    orlong,  # or-long
    xorlong,  # xor-long
    shllong,  # shl-long
    shrlong,  # shr-long
    ushrlong,  # ushr-long
    addfloat,  # add-float
    subfloat,  # sub-float
    mulfloat,  # mul-float
    divfloat,  # div-float
    remfloat,  # rem-float
    adddouble,  # add-double
    subdouble,  # sub-double
    muldouble,  # mul-double
    divdouble,  # div-double
    remdouble,  # rem-double
    # 0xb0
    addint2addr,  # add-int/2addr
    subint2addr,  # sub-int/2addr
    mulint2addr,  # mul-int/2addr
    divint2addr,  # div-int/2addr
    remint2addr,  # rem-int/2addr
    andint2addr,  # and-int/2addr
    orint2addr,  # or-int/2addr
    xorint2addr,  # xor-int/2addr
    shlint2addr,  # shl-int/2addr
    shrint2addr,  # shr-int/2addr
    ushrint2addr,  # ushr-int/2addr
    addlong2addr,  # add-long/2addr
    sublong2addr,  # sub-long/2addr
    mullong2addr,  # mul-long/2addr
    divlong2addr,  # div-long/2addr
    remlong2addr,  # rem-long/2addr
    # 0xc0
    andlong2addr,  # and-long/2addr
    orlong2addr,  # or-long/2addr
    xorlong2addr,  # xor-long/2addr
    shllong2addr,  # shl-long/2addr
    shrlong2addr,  # shr-long/2addr
    ushrlong2addr,  # ushr-long/2addr
    addfloat2addr,  # add-float/2addr
    subfloat2addr,  # sub-float/2addr
    mulfloat2addr,  # mul-float/2addr
    divfloat2addr,  # div-float/2addr
    remfloat2addr,  # rem-float/2addr
    adddouble2addr,  # add-double/2addr
    subdouble2addr,  # sub-double/2addr
    muldouble2addr,  # mul-double/2addr
    divdouble2addr,  # div-double/2addr
    remdouble2addr,  # rem-double/2addr
    # 0xd0
    addintlit16,  # add-int/lit16
    rsubint,  # rsub-int
    mulintlit16,  # mul-int/lit16
    divintlit16,  # div-int/lit16
    remintlit16,  # rem-int/lit16
    andintlit16,  # and-int/lit16
    orintlit16,  # or-int/lit16
    xorintlit16,  # xor-int/lit16
    addintlit8,  # add-int/lit8
    rsubintlit8,  # rsub-int/lit8
    mulintlit8,  # mul-int/lit8
    divintlit8,  # div-int/lit8
    remintlit8,  # rem-int/lit8
    andintlit8,  # and-int/lit8
    orintlit8,  # or-int/lit8
    xorintlit8,  # xor-int/lit8
    # 0xe0
    shlintlit8,  # shl-int/lit8
    shrintlit8,  # shr-int/lit8
    ushrintlit8,  # ushr-int/lit8
]
