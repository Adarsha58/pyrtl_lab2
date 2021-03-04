import pyrtl
from pyrtl import *

#creating a reusable mux
def two_one_mux(result, selector, res1, res2, opt_res3=0):
   with pyrtl.conditional_assignment:
      with selector == 0: 
         result |= res1
      with selector == 1: 
         result |= res2
      with selector == 2:
         result |= opt_res3

#creating control mux
def controller(control, op, funct):
   with conditional_assignment:
      with op == 0: 
         with funct == 0x20:  #add
            control |= 0x280
         with funct == 0x24:  #and
            control |= 0x282
         with funct == 0x2a: #slt
            control |= 0x284
      with op == 0x8:   #addi
         control |= 0xA0
      with op == 0xf:   #lui
         control |= 0xA5
      with op == 0xd:   #ori
         control |= 0xC3
      with op == 0x23:  #lw
         control |= 0xA8
      with op == 0x2b:  #sw
         control |= 0x30
      with op == 0x4:   #beq
         control |= 0x101


#creating main_alu
def main_alu(data0, data1, zero, alu_op, alu_out):
   #sets alu_out
   with conditional_assignment:
      with alu_op == 0:
         alu_out |= data0 + data1
      with alu_op == 1:
            alu_out |= data0 - data1
      with alu_op == 2:
         alu_out |= data0 & data1
      with alu_op == 3:
         alu_out |= data0 | data1
      with alu_op == 4:
         alu_out |= pyrtl.corecircuits.signed_lt(data0, data1)
      with alu_op == 5:
         alu_out |= pyrtl.corecircuits.shift_left_logical(data1, Const(16))
   
   #sets the zero register
   with conditional_assignment:
      with data0 == data1:
         zero |= 1
      with otherwise:
         zero |= 0


#all the needed building blocks
i_mem = MemBlock(bitwidth=32, addrwidth=32, name='i_mem')
d_mem = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name='d_mem', asynchronous=True)
rf    = MemBlock(bitwidth=32, addrwidth=5, name = 'rf', asynchronous=True)
pc    = Register(bitwidth=32, name='pc')

#main logic starts here
#get the instruction from the address pointed by pc
instr = WireVector(bitwidth=32, name='instr')
instr <<= i_mem[pc]

#setting up the decoder frpm last lab
op = WireVector(bitwidth=6, name='op')
rs = WireVector(bitwidth=5, name='rs')
rt = WireVector(bitwidth=5, name='rt')
rd = WireVector(bitwidth=5, name='rd')
sh = WireVector(bitwidth=5, name='sh')
func = WireVector(bitwidth=6, name='func')
imm = WireVector(bitwidth=16, name='imm')
addr = WireVector(bitwidth=26, name='addr')

op <<= instr[26:32]
rs <<= instr[21:26]
rt <<= instr[16:21]
rd <<= instr[11:16]
sh <<= instr[6:11]
func <<= instr[0:6]
imm <<= instr[0:16]
addr <<= instr[0:26]

#Control unit input and output wires
control = WireVector(bitwidth=10, name='control')
reg_dst = WireVector(bitwidth=1, name='reg_dst')
branch = WireVector(bitwidth=1, name='branch')
reg_w = WireVector(bitwidth=1, name='reg_w')
alu_src = WireVector(bitwidth=2, name='alu_src')
mem_w = WireVector(bitwidth=1, name='mem_w')
mem_to_reg = WireVector(bitwidth=1, name='mem_to_reg')
alu_op = WireVector(bitwidth=3, name='alu_op')


#setting the control output and its corresponding output wires
controller(control, op, func)
reg_dst <<= control[9]
branch <<= control[8]
reg_w <<= control[7]
alu_src <<= control[5:7]
mem_w <<= control[4]
mem_to_reg <<= control[3]
alu_op <<= control[0:3]

#setting up the read ports/ output wires for the register file memblock
rf_out_1 = WireVector(bitwidth=32, name='rf_out_1')
rf_out_2 = WireVector(bitwidth=32, name='rf_out_2')

rf_out_1 <<= rf[rs]
rf_out_2 <<= rf[rt]

#specifying write register for rf memblock
rf_write_reg = WireVector(bitwidth=5, name='rf_write_reg')
two_one_mux(rf_write_reg, reg_dst, rt, rd)

#setting up the alu inputs and outputs
alu_out = WireVector(bitwidth=32, name='alu_out')
alu_in_1 = WireVector(bitwidth=32, name='alu_in_1')
alu_in_2 = WireVector(bitwidth=32, name='alu_in_2')
zero = WireVector(bitwidth=1, name='zero')

alu_in_1 <<= rf_out_1
two_one_mux(alu_in_2, alu_src, rf_out_2, imm.sign_extended(32), imm.zero_extended(32))

#run the alu and save its output
main_alu(alu_in_1, alu_in_2, zero, alu_op, alu_out)


#setting the input/output wire for data_memory
d_mem_out = WireVector(bitwidth=32, name='d_mem_out')

d_mem[alu_out] <<= MemBlock.EnabledWrite(rf_out_2, enable=mem_w) #write port
d_mem_out <<= d_mem[alu_out]  #read port

#mux to choose between alu_out and d_mem_out
final_result = WireVector(bitwidth=32, name='final_result')
two_one_mux(final_result, mem_to_reg, alu_out, d_mem_out)

#write back to rf memblock
with conditional_assignment:
   with rf_write_reg != 0:
      rf[rf_write_reg] |= MemBlock.EnabledWrite(final_result, enable=reg_w)

#final part: updating pc and handling branches
branch_selector = WireVector(1, 'branch_selector')
branch_selector <<= branch & zero
with conditional_assignment:
   with branch_selector == 0:
      pc.next |= pc + 1
   with otherwise:
      pc.next |= pc + 1 + imm.sign_extended(32)



if __name__ == '__main__':

    """

    Here is how you can test your code.
    This is very similar to how the autograder will test your code too.

    1. Write a MIPS program. It can do anything as long as it tests the
       instructions you want to test.

    2. Assemble your MIPS program to convert it to machine code. Save
       this machine code to the "i_mem_init.txt" file.
       You do NOT want to use QtSPIM for this because QtSPIM sometimes
       assembles with errors. One assembler you can use is the following:

       https://alanhogan.com/asu/assembler.php

    3. Initialize your i_mem (instruction memory).

    4. Run your simulation for N cycles. Your program may run for an unknown
       number of cycles, so you may want to pick a large number for N so you
       can be sure that the program has "finished" its business logic.

    5. Test the values in the register file and memory to make sure they are
       what you expect them to be.

    6. (Optional) Debug. If your code didn't produce the values you thought
       they should, then you may want to call sim.render_trace() on a small
       number of cycles to see what's wrong. You can also inspect the memory
       and register file after every cycle if you wish.

    Some debugging tips:

        - Make sure your assembly program does what you think it does! You
          might want to run it in a simulator somewhere else (SPIM, etc)
          before debugging your PyRTL code.

        - Test incrementally. If your code doesn't work on the first try,
          test each instruction one at a time.

        - Make use of the render_trace() functionality. You can use this to
          print all named wires and registers, which is extremely helpful
          for knowing when values are wrong.

        - Test only a few cycles at a time. This way, you don't have a huge
          500 cycle trace to go through!

    """

    # Start a simulation trace
    sim_trace = pyrtl.SimulationTrace()

    # Initialize the i_mem with your instructions.
    i_mem_init = {}
    with open('i_mem_init.txt', 'r') as fin:
        i = 0
        for line in fin.readlines():
            i_mem_init[i] = int(line, 16)
            i += 1

    sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map={
        i_mem : i_mem_init
    })

    # Run for an arbitrarily large number of cycles.
    for cycle in range(500):
      sim.step({})
      

    # Use render_trace() to debug if your code doesn't work.
    # sim_trace.render_trace()

    #print(sim.inspect_mem(d_mem))
    #print(sim.inspect_mem(rf))

    # Perform some sanity checks to see if your program worked correctly
    #assert(sim.inspect_mem(d_mem)[0] == 10)
    #assert(sim.inspect_mem(rf)[8] == 10)    # $v0 = rf[8]
    #print('Passed!')
