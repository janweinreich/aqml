C     -*- fortran -*-
C     This file is autogenerated with f2py (version:2)
C     It contains Fortran 77 wrappers to fortran functions.

      subroutine f2pywrapfp_distance_double (a, b, d, p, f2py_a_d0
     &, f2py_a_d1, f2py_b_d0, f2py_b_d1, f2py_d_d0, f2py_d_d1)
      double precision p
      integer f2py_a_d0
      integer f2py_a_d1
      integer f2py_b_d0
      integer f2py_b_d1
      integer f2py_d_d0
      integer f2py_d_d1
      double precision a(f2py_a_d0,f2py_a_d1)
      double precision b(f2py_b_d0,f2py_b_d1)
      double precision d(f2py_d_d0,f2py_d_d1)
      interface
      subroutine fp_distance_double(a,b,d,p) 
          double precision, dimension(:,:),intent(in) :: a
          double precision, dimension(:,:),intent(in) :: b
          double precision, dimension(:,:),intent(inout) :: d
          double precision, intent(in) :: p
      end subroutine fp_distance_double
      end interface
      call fp_distance_double(a, b, d, p)
      end


      subroutine f2pywrapfp_distance_integer (a, b, d, p, f2py_a_d
     &0, f2py_a_d1, f2py_b_d0, f2py_b_d1, f2py_d_d0, f2py_d_d1)
      integer p
      integer f2py_a_d0
      integer f2py_a_d1
      integer f2py_b_d0
      integer f2py_b_d1
      integer f2py_d_d0
      integer f2py_d_d1
      double precision a(f2py_a_d0,f2py_a_d1)
      double precision b(f2py_b_d0,f2py_b_d1)
      double precision d(f2py_d_d0,f2py_d_d1)
      interface
      subroutine fp_distance_integer(a,b,d,p) 
          double precision, dimension(:,:),intent(in) :: a
          double precision, dimension(:,:),intent(in) :: b
          double precision, dimension(:,:),intent(inout) :: d
          integer, intent(in) :: p
      end subroutine fp_distance_integer
      end interface
      call fp_distance_integer(a, b, d, p)
      end

