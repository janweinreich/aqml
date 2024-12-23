
import numpy as np
import os,sys

def retrieve_esref(qcl):
    '''
    dbn -- database name
    qcl -- quantum chemitry level of method
    '''

    if qcl.lower() == 'vasp_pbe340': # in hartree
        esref = { 'H': [ -0.040932, 0, 0,  0],  # H
                  'C':    [ -0.050345, 0, 0,  0],  # C
                  'N':        [ -0.113673, 0, 0,  0],  # N
                  'O':        [ 0, 0, 0,  0],  # O
                  'F':        [ 0, 0, 0,  0],  # F
                  'P':        [ 0, 0, 0,  0],  # P
                  'S':        [ 0, 0, 0,  0],  # S
                  'Cl':        [ 0, 0, 0,  0],  # Cl
                  'B':        [ -0.017147, 0, 0,  0], # B
                  'Au':        [ -0.010520, 0, 0,  0], # Au
                  'Pt':        [ -0.031996, 0, 0,  0], # Pt
                  'Si':        [ -0.032019, 0, 0,  0] } # Si

    elif qcl.lower() == 'pm7': # in hartree
        #                   U (0 K)      U (298.15 K)    H (298.15 K)    G (298.15 K)
        esref = { 'H':[ 0,   0,  0.08302982, 0],  # H
                   'C':        [ 0,   0,  0.33113280, 0],  # C
                   'N':        [ 0,   0,  0.32047344, 0],  # N
                   'O':        [ 0,   0,  0.19984895, 0],  # O
                   'F':        [ 0,   0,  0.03010313, 0],  # F
                   'P':        [ 0,   0,  0.26244831, 0],  # P
                   'S':        [ 0,   0,  0.13237979, 0],  # S
                   'Cl':       [ 0,   0,  0.04588128, 0] } # Cl

    elif qcl.lower() == 'hfsto3g':
        esref = { 'H': [-0.466582,-0.465166,-0.464221,-0.477236],#H
                   'C':         [-37.198393,-37.196976,-37.196032,-37.212938],#C
                   'N':         [-53.719010,-53.717594,-53.716650,-53.734046],#N
                   'O':         [-73.804150,-73.802734,-73.801790,-73.819103],#O
                   'F':         [-97.986505,-97.985089,-97.984145,-98.001318],#F
                   'P':         [-336.868769,-336.867353,-336.866409,-336.884929],#P
                   'S':         [-393.130219,-393.128803,-393.127859,-393.146153],#S
                   'Cl':        [-454.542193,-454.540776,-454.539832,-454.557870] }#Cl

    elif qcl.lower() == 'hf631g2dfp':
        # default method: B3LYP/6-31G(2df,p)
        #           U (0 K)      U (298.15 K)    H (298.15 K)    G (298.15 K)
        esref = { 'H': [-0.498233,-0.496817,-0.495872,-0.508887],#H
                   'C':         [-37.682781,-37.681364,-37.680420,-37.697326],#C
                   'N':         [-54.385747,-54.384331,-54.383386,-54.400782],#N
                   'O':         [-74.787034,-74.785617,-74.784673,-74.801986],#O
                   'F':         [-99.367349,-99.365933,-99.364988,-99.382162],#F
                   'P':         [-340.690003,-340.688586,-340.687642,-340.706162],#P
                   'S':         [-397.478680,-397.477264,-397.476319,-397.494613],#S
                   'Cl':        [-459.450361,-459.448945,-459.448000,-459.466038] } #Cl

    elif qcl.lower() == 'hf631gd':
        # default method: B3LYP/6-31G(2df,p)
        #           U (0 K)      U (298.15 K)    H (298.15 K)    G (298.15 K)
        esref = { 'H':[-0.498233,-0.496817,-0.495872,-0.508887],#H
                   'C':        [-37.680860,-37.679444,-37.678500,-37.695406],#C
                   'N':        [-54.385442,-54.384026,-54.383082,-54.400478],#N
                   'O':        [-74.783934,-74.782517,-74.781573,-74.798886],#O
                   'F':        [-99.364957,-99.363541,-99.362596,-99.379770],#F
                   'P':        [-340.690204,-340.688788,-340.687844,-340.706364],#P
                   'S':        [-397.475958,-397.474541,-397.473597,-397.491891],#S
                   'Cl':       [-459.447964,-459.446548,-459.445603,-459.463641] } #,#Cl


    elif qcl.lower() == 'b3lyp631gd':
        # default method: B3LYP/6-31G(2df,p)
        #           U (0 K)      U (298.15 K)    H (298.15 K)    G (298.15 K)
        esref = { 'H': [-0.500273,-0.498857,-0.497912,-0.510927],#H
                  'C':          [-37.846280,-37.844864,-37.843920,-37.860826],#C
                  'N':          [-54.584489,-54.583073,-54.582129,-54.599525],#N
                  'O':          [-75.060623,-75.059207,-75.058263,-75.075575],#O
                  'F':          [-99.715536,-99.714120,-99.713176,-99.730350],#F
                  'P':          [-341.258090,-341.256674,-341.255729,-341.274250],#P
                  'S':          [-398.104993,-398.103577,-398.102632,-398.120926],#S
                  'Cl':         [-460.136242,-460.134826,-460.133882,-460.151919],#Cl
                  'B':         [-24.654355,-24.652939,-24.651994,-24.668395], #B
                  'Na':         [-162.279881,-162.278464,-162.277520,-162.294964] } #Na

    elif qcl.lower() == 'b3lyp631gdp':
        # default method: B3LYP/6-31G(2df,p)
        #           U (0 K)      U (298.15 K)    H (298.15 K)    G (298.15 K)
        esref = { 'H': [-0.500273,-0.498857,-0.497912,-0.510927],#H
                  'C':          [-37.846280,-37.844864,-37.843920,-37.860826],#C
                  'N':          [-54.584489,-54.583073,-54.582129,-54.599525],#N
                  'O':          [-75.060623,-75.059207,-75.058263,-75.075575],#O
                  'F':          [-99.715536,-99.714120,-99.713176,-99.730350],#F
                  'P':          [-341.258090,-341.256674,-341.255729,-341.274250],#P
                  'S':          [-398.104993,-398.103577,-398.102632,-398.120926],#S
                  'Cl':         [-460.136242,-460.134826,-460.133882,-460.151919]  } #Cl

    elif qcl.lower() == 'b3lyp631g2dfp':
        # default method: B3LYP/6-31G(2df,p)
        #           U (0 K)      U (298.15 K)    H (298.15 K)    G (298.15 K)
        esref = { 'H':[ -0.500273,-0.498857,-0.497912,-0.510927],#H
                  'C':         [  -37.846772,-37.845355,-37.844411,-37.861317],#C
                  'N':         [  -54.583861,-54.582445,-54.581501,-54.598897],#N
                  'O':         [  -75.064579,-75.063163,-75.062219,-75.079532],#O
                  'F':         [  -99.718730,-99.717314,-99.716370,-99.733544],#F
                  'P':         [  -341.257555,-341.256138,-341.255194,-341.273714],#P
                  'S':         [  -398.105756,-398.104340,-398.103396,-398.121689],#S
                  'Cl':        [  -460.136686,-460.135270,-460.134325,-460.152363] }#Cl

    elif qcl.lower() == 'mp2631g2dfp':
        esref = { 'H':[-0.498233,-0.496817,-0.495872,-0.508887],#H
                  'C':         [-37.745228,-37.743812,-37.742867,-37.759773],#C
                  'N':         [-54.474019,-54.472603,-54.471658,-54.489054],#N
                  'O':         [-74.916014,-74.914598,-74.913654,-74.930967],#O
                  'F':         [-99.539287,-99.537871,-99.536927,-99.554100],#F
                  'P':         [-340.767994,-340.766577,-340.765633,-340.784154],#P
                  'S':         [-397.586190,-397.584773,-397.583829,-397.602123],#S
                  'Cl':        [-459.595376,-459.593959,-459.593015,-459.611053] }#Cl

    elif qcl.lower() == 'mp2631gd':
        esref = {   'H':       [-0.498233,-0.496817,-0.495872,-0.508887],#H
                    'C':       [-37.732974,-37.731558,-37.730614,-37.747520],#C
                    'N':       [-54.457008,-54.455592,-54.454647,-54.472043],#N
                    'O':       [-74.880037,-74.878620,-74.877676,-74.894989],#O
                    'F':       [-99.487271,-99.485855,-99.484911,-99.502084],#F
                    'P':       [-340.746888,-340.745472,-340.744527,-340.763048],#P
                    'S':       [-397.553377,-397.551961,-397.551017,-397.569310],#S
                    'Cl':      [-459.552433,-459.551017,-459.550073,-459.568111] } #Cl

    elif qcl.lower() == 'g4mp2':
         esref = { 'H': [-0.502094,-0.500677,-0.499733,-0.512748],#H
                   'C': [-37.794203,-37.792787,-37.791842,-37.808748],#C
                   'N': [-54.532825,-54.531408,-54.530464,-54.547860],#N
                   'O': [-75.002483,-75.001067,-75.000122,-75.017435],#O
                   'F': [-99.659686,-99.658269,-99.657325,-99.674499],#F
                   'P': [-340.837016,-340.835599,-340.834655,-340.853176],#P
                   'S': [-397.676523,-397.675107,-397.674163,-397.692456],#S
                   'Cl':[-459.703691,-459.702274,-459.701330,-459.719368] }#Cl

    else:
        print ' #ERROR: no such method -- %s!'%qcl.lower(); sys.exit(2)

    return esref

def get_es0(zs0, qcl): #):

    esref, zsref = retrieve_esref(qcl)

    es0 = np.zeros(4)
    for zi0 in zs0:
        es0_ = esref[np.where(zsref == zi0)[0], :]
        es0 = es0 + np.array(es0_[0])

    return es0

def get_ae0(zs0, qcl):
    return get_es0(zs0,qcl)[0]

def get_ae(atoms, Em, qcl, idx):
    """
    get atomization energy of U0
    """
    es0 = get_es0(atoms.numbers, qcl)
    return Em - es0[idx]

