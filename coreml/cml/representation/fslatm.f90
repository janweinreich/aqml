


subroutine calc_sbot(coordinates, nuclear_charges, cg, izeff, z1, z2, z3, rcut, nx, dgrid, sigma, coeff, ys)

    use utils, only: linspace, calc_angle, calc_cos_angle
    use atomdb

    implicit none
    logical, intent(in) :: izeff

    double precision, dimension(:,:), intent(in) :: coordinates
    double precision, dimension(:), intent(in) :: nuclear_charges
    integer, dimension(:,:), intent(in) :: cg
    double precision, intent(in) :: rcut
    integer, intent(in) :: nx
    double precision, intent(in) :: dgrid
    double precision, intent(in) :: sigma
    double precision, intent(in) :: coeff
    double precision, dimension(nx), intent(out) :: ys

    ! MBtype
    integer, intent(in) :: z1, z2, z3

    integer, dimension(:), allocatable :: ias1, ias2, ias3
    integer :: nias1, nias2, nias3

    integer :: ia1, ia2, ia3

    double precision, allocatable, dimension(:, :) :: distance_matrix

    double precision :: norm

    integer :: i, j, k
    integer :: natoms

    double precision, parameter :: eps = epsilon(0.0d0)
    double precision, parameter :: pi = 4.0d0 * atan(1.0d0)
    double precision :: d2r
    double precision :: c0
    double precision :: ang
    double precision :: cak
    double precision :: cai
    double precision :: prefactor
    double precision :: r
    double precision :: a0, a1
    double precision, dimension(nx) :: xs
    double precision, dimension(nx) :: cos_xs
    double precision :: inv_sigma

    natoms = size(coordinates, dim=1)
    if (size(coordinates, dim=1) /= size(nuclear_charges, dim=1)) then
        write(*,*) "ERROR: Coulomb matrix generation"
        write(*,*) size(coordinates, dim=1), "coordinates, but", &
            & size(nuclear_charges, dim=1), "atom_types!"
        stop
    endif

    ! Allocate temporary
    allocate(distance_matrix(natoms, natoms))
    distance_matrix = 0.0d0

    !$OMP PARALLEL DO PRIVATE(norm)
    do i = 1, natoms
        do j = i+1, natoms
            norm = sqrt(sum((coordinates(j,:) - coordinates(i,:))**2))
            distance_matrix(i, j) = norm
            distance_matrix(j, i) = norm
        enddo
    enddo
    !$OMP END PARALLEL DO

    allocate(ias1(natoms))
    allocate(ias2(natoms))
    allocate(ias3(natoms))

    ias1 = 0
    ias2 = 0
    ias3 = 0

    nias1 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z1) then
            nias1 = nias1 + 1
            ias1(nias1) = i
        endif
    enddo

    nias2 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z2) then
            nias2 = nias2 + 1
            ias2(nias2) = i
        endif
    enddo 

    nias3 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z3) then
            nias3 = nias3 + 1
            ias3(nias3) = i
        endif
    enddo

    d2r = pi/180.0d0
    a0 = -20.0d0 * d2r
    a1 = pi + 20.0d0 * d2r

    xs = linspace(a0, a1, nx)


    prefactor = 1.0d0 ! use connectivity between atoms 
    if ( all(cg .eq. 1) ) prefactor = 1.0d0 / 3.0d0 ! enumerate all possible triples of atoms (unless d_ij > rcut)
    !
    if ( izeff ) then
        c0 = prefactor * (zstar(z1)*zstar(z2)*zstar(z3)) * coeff * dgrid
    else
        c0 = prefactor * (mod(z1,1000)*mod(z2,1000)*mod(z3,1000)) * coeff * dgrid
    endif

    ys = 0.0d0
    inv_sigma = -1.0d0 / (2*sigma**2)

    !$OMP PARALLEL DO
    do i = 1, nx
        cos_xs(i) = cos(xs(i)) * c0
    enddo
    !$OMP END PARALLEL do


    if (z1 == z3) then

        !$OMP PARALLEL DO PRIVATE(i,j,k,ang,cai,cak,r) REDUCTION(+:ys) SCHEDULE(DYNAMIC)
        do ia1 = 1, nias1
            do ia2 = 1, nias2 !! `ia2 is the central atom
                if ( cg(ias2(ia2),ias1(ia1)) .eq. 0 ) cycle

                ! d(ia1,ia2) > 0 ensures that `ia2 & `ia1 do not correspond to the same atom 
                if (.not. ((distance_matrix(ias1(ia1),ias2(ia2)) > eps) .and. &
                         & (distance_matrix(ias1(ia1),ias2(ia2)) <= rcut))) cycle
                do ia3 = ia1 + 1, nias3
                    if ( cg(ias2(ia2),ias3(ia3)) .eq. 0 ) cycle
                    if (distance_matrix(ias1(ia1),ias3(ia3)) > rcut) cycle

                    ! d(ia2,ia3) > 0 ensures that `ia2 & `ia3 do not correspond to the same atom 
                    if (.not. ((distance_matrix(ias2(ia2),ias3(ia3)) > eps) .and. & 
                             & (distance_matrix(ias2(ia2),ias3(ia3)) <= rcut))) cycle

                        i = ias1(ia1)
                        j = ias2(ia2)
                        k = ias3(ia3)

                        ang = calc_angle(coordinates(i, :), coordinates(j, :), coordinates(k, :))
                        cak = calc_cos_angle(coordinates(i, :), coordinates(k, :), coordinates(j, :))
                        cai = calc_cos_angle(coordinates(k, :), coordinates(i, :), coordinates(j, :))

                        r = distance_matrix(i,j) * distance_matrix(i,k) * distance_matrix(k,j)

                        ys = ys + (c0 + cos_xs*cak*cai)/(r**3) * ( exp((xs-ang)**2 * inv_sigma) )
                enddo
            enddo
        enddo
        !$OMP END PARALLEL do

    else

        !$OMP PARALLEL DO PRIVATE(i,j,k,ang,cai,cak,r) REDUCTION(+:ys) SCHEDULE(DYNAMIC)
        do ia1 = 1, nias1
            do ia2 = 1, nias2
                if ( cg(ias1(ia1),ias2(ia2)) .eq. 0 ) cycle
                if (.not. ((distance_matrix(ias1(ia1),ias2(ia2)) > eps) .and. &
                         & (distance_matrix(ias1(ia1),ias2(ia2)) <= rcut))) cycle
                do ia3 = 1, nias3
                    if ( cg(ias1(ia2),ias3(ia3)) .eq. 0 ) cycle
                    if (distance_matrix(ias1(ia2),ias3(ia3)) > rcut) cycle
                    if (.not. ((distance_matrix(ias2(ia2),ias3(ia3)) > eps) .and. &
                             & (distance_matrix(ias2(ia2),ias3(ia3)) <= rcut))) cycle

                        i = ias1(ia1)
                        j = ias2(ia2)
                        k = ias3(ia3)

                        ang = calc_angle(coordinates(i, :), coordinates(j, :), coordinates(k, :))
                        cak = calc_cos_angle(coordinates(i, :), coordinates(k, :), coordinates(j, :))
                        cai = calc_cos_angle(coordinates(k, :), coordinates(i, :), coordinates(j, :))

                        r = distance_matrix(i,j) * distance_matrix(i,k) * distance_matrix(k,j)
                        ys = ys + (c0 + cos_xs*cak*cai)/(r**3 ) * ( exp((xs-ang)**2 * inv_sigma) )

                enddo
            enddo
        enddo
        !$OMP END PARALLEL do

    endif

    deallocate(ias1)
    deallocate(ias2)
    deallocate(ias3)
    deallocate(distance_matrix)

end subroutine calc_sbot



subroutine calc_sbot_local(coordinates, nuclear_charges, ia_python, cg, izeff, z1, z2, z3, rcut, nx, dgrid, sigma, coeff, ys)

    use utils, only: linspace, calc_angle, calc_cos_angle
    use atomdb
    implicit none
    logical, intent(in) :: izeff

    double precision, dimension(:,:), intent(in) :: coordinates
    double precision, dimension(:), intent(in) :: nuclear_charges
    integer, dimension(:,:), intent(in) :: cg
    double precision, intent(in) :: rcut
    integer, intent(in) :: nx
    integer, intent(in) :: ia_python
    double precision, intent(in) :: dgrid
    double precision, intent(in) :: sigma
    double precision, intent(in) :: coeff
    double precision, dimension(nx), intent(out) :: ys

    ! MBtype
    integer, intent(in) :: z1, z2, z3

    integer, dimension(:), allocatable :: ias1, ias2, ias3
    integer :: nias1, nias2, nias3

    integer :: ia1, ia2, ia3

    double precision, allocatable, dimension(:, :) :: distance_matrix

    double precision :: norm

    integer :: i, j, k
    integer :: natoms

    double precision, parameter :: eps = epsilon(0.0d0)
    double precision, parameter :: pi = 4.0d0 * atan(1.0d0)
    double precision :: d2r
    double precision :: c0
    double precision :: ang
    double precision :: cak
    double precision :: cai
    double precision :: prefactor
    double precision :: r
    double precision :: a0, a1
    double precision, dimension(nx) :: xs
    double precision, dimension(nx) :: cos_xs
    double precision :: inv_sigma

    logical :: stop_flag

    integer :: ia
    ia = ia_python + 1

    natoms = size(coordinates, dim=1)
    if (size(coordinates, dim=1) /= size(nuclear_charges, dim=1)) then
        write(*,*) "ERROR: Coulomb matrix generation"
        write(*,*) size(coordinates, dim=1), "coordinates, but", &
            & size(nuclear_charges, dim=1), "atom_types!"
        stop
    endif

    ! Allocate temporary
    allocate(distance_matrix(natoms, natoms))
    distance_matrix = 0.0d0

    !$OMP PARALLEL DO PRIVATE(norm)
    do i = 1, natoms
        do j = i+1, natoms
            norm = sqrt(sum((coordinates(j,:) - coordinates(i,:))**2))
            distance_matrix(i, j) = norm
            distance_matrix(j, i) = norm
        enddo
    enddo
    !$OMP END PARALLEL DO

    allocate(ias1(natoms))
    allocate(ias2(natoms))
    allocate(ias3(natoms))

    ias1 = 0
    ias2 = 0
    ias3 = 0

    nias1 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z1) then
            nias1 = nias1 + 1
            ias1(nias1) = i
        endif
    enddo

    nias2 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z2) then
            nias2 = nias2 + 1
            ias2(nias2) = i
        endif
    enddo 

    nias3 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z3) then
            nias3 = nias3 + 1
            ias3(nias3) = i
        endif
    enddo

    stop_flag = .true.
    do ia2 = 1, nias2
        if (ias2(ia2) == ia) stop_flag = .false.
    enddo
    if (stop_flag) return

    d2r = pi/180.0d0
    a0 = -20.0d0 * d2r
    a1 = pi + 20.0d0 * d2r

    xs = linspace(a0, a1, nx)

    prefactor = 1.0d0 ! use connectivity between atoms 
    if ( all(cg .eq. 1) ) prefactor = 1.0d0 / 3.0d0 ! enumerate all possible triples of atoms (unless d_ij > rcut)

    !
    if ( izeff ) then
        c0 = prefactor * (zstar(z1)*zstar(z2)*zstar(z3)) * coeff * dgrid
    else
        c0 = prefactor * (mod(z1,1000)*mod(z2,1000)*mod(z3,1000)) * coeff * dgrid
    endif

    ys = 0.0d0
    inv_sigma = -1.0d0 / (2*sigma**2)

    !$OMP PARALLEL DO
    do i = 1, nx
        cos_xs(i) = cos(xs(i)) * c0
    enddo
    !$OMP END PARALLEL do

    if (z1 == z3) then

        !$OMP PARALLEL DO PRIVATE(i,j,k,ang,cai,cak,r) REDUCTION(+:ys) SCHEDULE(DYNAMIC)
        do ia1 = 1, nias1
            if ( cg(ia,ias1(ia1)) .eq. 0 ) cycle
            if (.not. ((distance_matrix(ias1(ia1),ia) > eps) .and. &
                     & (distance_matrix(ias1(ia1),ia) <= rcut))) cycle
            do ia3 = ia1 + 1, nias3
                if ( cg(ia,ias3(ia3)) .eq. 0 ) cycle
                if (distance_matrix(ias1(ia1),ias3(ia3)) > rcut) cycle !!!!!!!!!!
                if (.not. ((distance_matrix(ia,ias3(ia3)) > eps) .and. &
                         & (distance_matrix(ia,ias3(ia3)) <= rcut))) cycle

                    i = ias1(ia1)
                    j = ia
                    k = ias3(ia3)

                    ang = calc_angle(coordinates(i, :), coordinates(j, :), coordinates(k, :))
                    cak = calc_cos_angle(coordinates(i, :), coordinates(k, :), coordinates(j, :))
                    cai = calc_cos_angle(coordinates(k, :), coordinates(i, :), coordinates(j, :))

                    r = distance_matrix(i,j) * distance_matrix(i,k) * distance_matrix(k,j)

                    ys = ys + (c0 + cos_xs*cak*cai)/(r**3) * ( exp((xs-ang)**2 * inv_sigma) )

            enddo
        enddo
        !$OMP END PARALLEL do

    else

        !$OMP PARALLEL DO PRIVATE(i,j,k,ang,cai,cak,r) REDUCTION(+:ys) SCHEDULE(DYNAMIC)
        do ia1 = 1, nias1
            if ( cg(ia,ias1(ia1)) .eq. 0 ) cycle
            if (.not. ((distance_matrix(ias1(ia1),ia) > eps) .and. &
                     & (distance_matrix(ias1(ia1),ia) <= rcut))) cycle
            do ia3 = 1, nias3
                if ( cg(ia,ias3(ia3)) .eq. 0 ) cycle
                if (distance_matrix(ias1(ia1),ias3(ia3)) > rcut) cycle
                if (.not. ((distance_matrix(ia,ias3(ia3)) > eps) .and. &
                         & (distance_matrix(ia,ias3(ia3)) <= rcut))) cycle

                    i = ias1(ia1)
                    j = ia
                    k = ias3(ia3)

                    ang = calc_angle(coordinates(i, :), coordinates(j, :), coordinates(k, :))
                    cak = calc_cos_angle(coordinates(i, :), coordinates(k, :), coordinates(j, :))
                    cai = calc_cos_angle(coordinates(k, :), coordinates(i, :), coordinates(j, :))

                    r = distance_matrix(i,j) * distance_matrix(i,k) * distance_matrix(k,j)
                    ys = ys + (c0 + cos_xs*cak*cai)/(r**3 ) * ( exp((xs-ang)**2 * inv_sigma) )

            enddo
        enddo
        !$OMP END PARALLEL do

    endif



    deallocate(ias1)
    deallocate(ias2)
    deallocate(ias3)
    deallocate(distance_matrix)

end subroutine calc_sbot_local



subroutine calc_sbop(coordinates, nuclear_charges, cg, izeff, z1, z2, rcut, nx, dgrid, sigma, coeff, rpower, ys)

    use utils, only: linspace
    use atomdb
    implicit none
    logical, intent(in) :: izeff

    double precision, dimension(:,:), intent(in) :: coordinates
    double precision, dimension(:), intent(in) :: nuclear_charges
    integer, dimension(:,:), intent(in) :: cg
    double precision, intent(in) :: rcut
    integer, intent(in) :: nx
    double precision, intent(in) :: dgrid
    double precision, intent(in) :: sigma
    double precision, intent(in) :: rpower
    double precision, intent(in) :: coeff
    double precision, dimension(nx), intent(out) :: ys

    integer, intent(in) :: z1, z2

    double precision :: r0
    double precision :: r
    double precision :: rcut2
    integer :: i
    integer :: natoms

    integer, dimension(:), allocatable :: ias1, ias2
    integer :: nias1, nias2

    integer :: ia1, ia2
    double precision, parameter :: eps = epsilon(0.0d0)
    double precision, dimension(nx) :: xs
    double precision, parameter :: pi = 4.0d0 * atan(1.0d0)
    double precision :: c0
    double precision :: inv_sigma

    double precision, dimension(nx) :: xs0

    natoms = size(coordinates, dim=1)
    if (size(coordinates, dim=1) /= size(nuclear_charges, dim=1)) then
        write(*,*) "ERROR: Coulomb matrix generation"
        write(*,*) size(coordinates, dim=1), "coordinates, but", &
            & size(nuclear_charges, dim=1), "atom_types!"
        stop
    endif

    allocate(ias1(natoms))
    allocate(ias2(natoms))

    ias1 = 0
    ias2 = 0

    nias1 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z1) then
            nias1 = nias1 + 1
            ias1(nias1) = i
        endif
    enddo

    nias2 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z2) then
            nias2 = nias2 + 1
            ias2(nias2) = i
        endif
    enddo


    r0 = 0.1d0
    xs = linspace(r0, rcut, nx)
    ys = 0.0d0

    !
    if ( izeff ) then
        c0 = (zstar(z1)*zstar(z2)) * coeff
    else
        c0 = (mod(z1,1000)*mod(z2,1000)) * coeff
    endif

    inv_sigma = -0.5d0 / sigma**2 
    xs0 = c0/(xs**rpower) * dgrid

    rcut2 = rcut**2

    if (z1.eq.z2) then

        !$OMP PARALLEL DO REDUCTION(+:ys)
        do ia1 = 1, nias1
            do ia2 = ia1 + 1, nias2
                if ( cg(ias1(ia1),ias2(ia2)) .eq. 0 ) cycle
                r = sum((coordinates(ias1(ia1),:) - coordinates(ias2(ia2),:))**2)
                if (r < rcut2) ys = ys + xs0 * exp( inv_sigma * (xs - sqrt(r))**2 )
            enddo
        enddo
        !$OMP END PARALLEL DO

    else

        !$OMP PARALLEL DO REDUCTION(+:ys)
        do ia1 = 1, nias1
            do ia2 = 1, nias2
                if ( cg(ias1(ia1),ias2(ia2)) .eq. 0 ) cycle
                r = sum((coordinates(ias1(ia1),:) - coordinates(ias2(ia2),:))**2)
                if (r < rcut2) ys = ys + xs0 * exp( inv_sigma * (xs - sqrt(r))**2 )
            enddo
        enddo
        !$OMP END PARALLEL DO

    endif

    deallocate(ias1)
    deallocate(ias2)

end subroutine calc_sbop



subroutine calc_sbop_local(coordinates, nuclear_charges, ia_python, cg, izeff, z1, z2, rcut, nx, dgrid, sigma, coeff, rpower, ys)

    use utils, only: linspace
    use atomdb
    implicit none
    logical, intent(in) :: izeff

    double precision, dimension(:,:), intent(in) :: coordinates
    double precision, dimension(:), intent(in) :: nuclear_charges
    integer, dimension(:,:), intent(in) :: cg
    double precision, intent(in) :: rcut
    integer, intent(in) :: nx
    integer, intent(in) :: ia_python
    double precision, intent(in) :: dgrid
    double precision, intent(in) :: sigma
    double precision, intent(in) :: rpower
    double precision, intent(in) :: coeff
    double precision, dimension(nx), intent(out) :: ys

    integer, intent(in) :: z1, z2

    double precision :: r0
    double precision :: r
    double precision :: rcut2
    integer :: i
    integer :: natoms

    integer, dimension(:), allocatable :: ias1, ias2
    integer :: nias1, nias2

    integer :: ia1, ia2
    double precision, parameter :: eps = epsilon(0.0d0)
    double precision, dimension(nx) :: xs
    double precision, parameter :: pi = 4.0d0 * atan(1.0d0)
    double precision :: c0
    double precision :: inv_sigma

    double precision, dimension(nx) :: xs0
    integer :: ia

    double precision :: prefactor

    ia = ia_python + 1

    natoms = size(coordinates, dim=1)
    if (size(coordinates, dim=1) /= size(nuclear_charges, dim=1)) then
        write(*,*) "ERROR: Coulomb matrix generation"
        write(*,*) size(coordinates, dim=1), "coordinates, but", &
            & size(nuclear_charges, dim=1), "atom_types!"
        stop
    endif

    allocate(ias1(natoms))
    allocate(ias2(natoms))

    ias1 = 0
    ias2 = 0

    nias1 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z1) then
            nias1 = nias1 + 1
            ias1(nias1) = i
        endif
    enddo

    nias2 = 0
    do i = 1, natoms
        if (int(nuclear_charges(i)).eq.z2) then
            nias2 = nias2 + 1
            ias2(nias2) = i
        endif
    enddo


    r0 = 0.1d0
    xs = linspace(r0, rcut, nx)
    ys = 0.0d0

    prefactor = 1.0d0 ! use connectivity between atoms 
    if ( all(cg .eq. 1) ) prefactor = 1.0d0 / 2.0d0 ! enumerate all possible triples of atoms (unless d_ij > rcut)

    if ( izeff ) then
        c0 = prefactor * (zstar(z1)*zstar(z2)) * coeff
    else
        c0 = prefactor * (mod(z1,1000)*mod(z2,1000)) * coeff
    endif

    inv_sigma = -0.5d0 / sigma**2 
    xs0 = c0/(xs**rpower) * dgrid

    rcut2 = rcut**2

    if (z1.eq.z2) then

        !$OMP PARALLEL DO REDUCTION(+:ys)
        do ia1 = 1, nias1
            do ia2 = ia1 + 1, nias2
                if ( cg(ias1(ia1),ias2(ia2)) .eq. 0 ) cycle
                if ((ias1(ia1) /= ia).and.(ias2(ia2)/= ia)) cycle
                r = sum((coordinates(ias1(ia1),:) - coordinates(ias2(ia2),:))**2)
                if (r < rcut2) ys = ys + xs0 * exp( inv_sigma * (xs - sqrt(r))**2 )
            enddo
        enddo
        !$OMP END PARALLEL DO

    else

        !$OMP PARALLEL DO REDUCTION(+:ys)
        do ia1 = 1, nias1
            do ia2 = 1, nias2
                if ( cg(ias1(ia1),ias2(ia2)) .eq. 0 ) cycle
                if ((ias1(ia1) /= ia).and.(ias2(ia2)/= ia)) cycle
                r = sum((coordinates(ias1(ia1),:) - coordinates(ias2(ia2),:))**2)
                if (r < rcut2) ys = ys + xs0 * exp( inv_sigma * (xs - sqrt(r))**2 )
            enddo
        enddo
        !$OMP END PARALLEL DO

    endif

    deallocate(ias1)
    deallocate(ias2)

end subroutine calc_sbop_local


