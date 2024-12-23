

Suppose we are given a target molecule (a QM9 molecule containing 9 heavy atoms), with geometrical information stored in file `target/01.sdf`, our aim is to predict its total energy trained on a set of smaller fragments (amons) containing no more than 7 heavy atoms.

## Amons generation

First of all, we generate amons of the target molecule. The initial geometries were optimized by force field approaches during amons generation. The code to do this is:

```bash
genamon target/01.sdf
```

Then a folder named `g7` would be created, including sdf files of corresponding amons.


## Running quantum chemical calculations

Before preceding, a copy of the quantum chemistry program `orca 4` has to be acquired (for downloads, fill the registration form at https://cec.mpg.de/orcadownload/).
Once `orca` is installed, specify the following environment variable:

```bash
export orca4=/path/of/orca_binary
```

For generation of quantum chemical reference data for training/test, here we consider only the ground state geometry and energy of the target QM9 molecule calculated at B3LYP/cc-pVDZ level. Three consecutive steps are necessary:

  - First generate input files for ORCA 4:
```bash
gen_orca_jobs -loose -t optg -m b3lyp -b vdz -n 1 g7/*.sdf 
```
The option `-n 1` specifies the number of processes to be used. Choose a larger number to speed up computations. For target molecule (i.e., `target/01.sdf`), remove the option `-loose`.

  - Then run orca4 jobs serially through calling the script `batch_orca`:
```bash
batch_orca g7/*.com target/*.com >out1 &
```


Reference input & output files of orca4 jobs are provided under folder `reference/` with suffix `.com` and `.out`, respectively.

  - Convert output files to xyz format once all calculations are done:
```bash
orca2xyz -p e g7/*.out target/*.out
```
The resulting `xyz` files contain relaxed geometries, the same as the usual `xyz` file format-wise. Poperties (only energy as the default case) is written to the second line, with the format of, say `b3lypvdz=-40.0321`, meaning the single point energy calculated at the level B3LYP/cc-pVDZ is -40.0321 Hartree (Atomic unit is the default for all properties in `xyz` files).

## AML prediction

```bash

aqml -train g7/ -test target/
```

Outputs:
```bash
    coeff= 1.0 llambda= 0.0001
   1      1    1167.1923    1167.1923  (DressedAtom mae=  -1882.0703)
   2      3     130.1885     130.1885  (DressedAtom mae=    130.1885)
   3      5      66.9106      66.9106  (DressedAtom mae=     74.5169)
   4      6      47.5368      47.5368  (DressedAtom mae=     76.0269)               ```
   5     10      40.1071      40.1071  (DressedAtom mae=     51.3559)
   6     11       0.8773      -0.8773  (DressedAtom mae=     17.4143)
   7     16       0.2251       0.2251  (DressedAtom mae=     17.9935)
 elapsed time:  0.5318758487701416  seconds
```
The above output shows that AML upderestimate the total energy of the target molecule by 0.2251 kcal/mol, after training on 16 amons containing at most 7 heavy atoms.

To print out atomic contribution to the atomization energy, add two more options in the commandline, I.e.,

Running
```bash
aqml -train g7 -test target -p b3lypvdz -ieaq -prog orca 
```
gives in addition to the above output, also
```bash
atomic energies
    #atm  #Z     #E_A 
       1   6  -163.80
       2   6  -163.55
       3   6  -163.57
       4   6  -163.55
       5   6  -163.77
       6   6  -163.42
       7   6  -159.70
       8   6  -161.60
       9   8   -90.76
      10   1   -59.83
      11   1   -59.98
      12   1   -59.99
      13   1   -59.98
      14   1   -59.78
      15   1   -64.12
      16   1   -63.75
      17   1   -60.70
 elapsed time:  0.5318758487701416  seconds
```


