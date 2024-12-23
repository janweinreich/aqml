%pal nprocs 2 end
%maxcore 1000
! b3lyp TIGHTSCF
! cc-pvdz def2/J RIJCOSX
! Opt

%geom
maxiter 60
TolE 1e-4
TolRMSG 2e-3
TolMaxG 3e-3
TolRMSD 2e-2
TolMaxD 3e-2
end

*xyz 0 1
C 2.6819 -0.4448 -0.2357
C 1.6938 -1.2326 0.2055
C 0.3275 -0.8453 0.4826
C -0.204 0.3797 0.3516
C -1.6209 0.7086 0.6964
H 3.6725 -0.8548 -0.4068
H 1.9158 -2.2842 0.3847
H -0.302 -1.6561 0.8487
H -2.1731 -0.1633 1.061
H -1.6457 1.4778 1.4743
H 2.5475 0.6112 -0.4385
H 0.3951 1.2119 -0.0064
H -2.1385 1.0953 -0.1868
*

