%pal nprocs 16 end
%maxcore 1000
! Opt b3lyp TIGHTSCF
! cc-pvdz def2/J RIJCOSX


*xyz 0 1
C 0.781219 1.30318 -0.123886
C 2.099689 0.952529 -0.420476
C 2.529552 -0.361899 -0.239222
C 1.633903 -1.321283 0.238811
C 0.318583 -0.967424 0.535281
C -0.12328 0.350864 0.358685
C -1.544416 0.739753 0.68526
C -2.626598 0.0655 -0.146437
O -2.457674 -0.838142 -0.930882
H 0.451985 2.330186 -0.267503
H 2.788226 1.70682 -0.792207
H 3.55514 -0.638412 -0.46882
H 1.960073 -2.348363 0.379793
H -0.373487 -1.721687 0.899339
H -1.793359 0.511866 1.735434
H -1.691794 1.825023 0.592172
H -3.6473 0.472396 0.040745
*
