# -*- coding: utf-8 -*-
import os
from os.path import join as opj
import importlib
import json
import sys

from ost.helpers import helpers as h


def _import(infile, out_prefix, logfile, swath, burst, polar='VV,VH,HH,HV'):
    '''A wrapper of SNAP import of a single Sentinel-1 SLC burst

    This function takes an original Sentinel-1 scene (either zip or
    SAFE format), updates the orbit information (does not fail if not
    available), and extracts a single burst based on the
    given input parameters.

    Args:
        infile: string or os.path object for
                an original Sentinel-1 GRD product in zip or SAFE format
        out_prefix: string or os.path object for the output
                    file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to
        swath (str): the corresponding IW subswath of the burst
        burst (str): the burst number as in the Sentinel-1 annotation file
        polar (str): a string consisiting of the polarisation (comma separated)
                     e.g. 'VV,VH',
                     default value: 'VV,VH,HH,HV'

    '''

    # get gpt file
    gpt_file = h.gpt_path()

    # get path to graph
    rootpath = importlib.util.find_spec('ost').submodule_search_locations[0]
    graph = opj(rootpath, 'graphs', 'S1_SLC2ARD', 'S1_SLC_BurstSplit_AO.xml')

    print(' INFO: Importing Burst {} from Swath {}'
          ' from scene {}'.format(burst, swath, os.path.basename(infile)))

    command = '{} {} -x -q {} -Pinput={} -Ppolar={} -Pswath={}\
                      -Pburst={} -Poutput={}' \
        .format(gpt_file, graph, os.cpu_count(), infile, polar, swath,
                burst, out_prefix)

    return_code = h.run_command(command, logfile)

    if return_code == 0:
        print(' INFO: Succesfully imported product')
    else:
        print(' ERROR: Frame import exited with an error. \
                See {} for Snap Error output'.format(logfile))
        # sys.exit(119)

    return return_code


def _ha_alpha(infile, outfile, logfile, pol_speckle_filter=False):
    '''A wrapper of SNAP H-A-alpha polarimetric decomposition

    This function takes an OST imported Sentinel-1 scene/burst
    and calulates the polarimetric decomposition parameters for
    the H-A-alpha decomposition.

    Args:
        infile: string or os.path object for
                an original Sentinel-1 GRD product in zip or SAFE format
        out_prefix: string or os.path object for the output
                    file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to
        pol_speckle_filter (bool): wether or not to apply the
                                   polarimetric speckle filter

    '''

    # get gpt file
    gpt_file = h.gpt_path()

    # get path to graph
    rootpath = importlib.util.find_spec('ost').submodule_search_locations[0]

    if pol_speckle_filter:
        graph = opj(rootpath, 'graphs', 'S1_SLC2ARD',
                    'S1_SLC_Deb_Spk_Halpha.xml')
    else:
        graph = opj(rootpath, 'graphs', 'S1_SLC2ARD',
                    'S1_SLC_Deb_Halpha.xml')

    print(" INFO: Calculating the H-alpha dual polarisation")
    command = '{} {} -x -q {} -Pinput={} -Poutput={}' \
        .format(gpt_file, graph, 2 * os.cpu_count(), infile, outfile)

    return_code = h.run_command(command, logfile)

    if return_code == 0:
        print(' INFO: Succesfully created H/Alpha product')
    else:
        print(' ERROR: H/Alpha exited with an error. \
                See {} for Snap Error output'.format(logfile))
        # sys.exit(121)

    return return_code


def _calibration(infile, outfile, logfile, product_type='GTCgamma'):
    '''A wrapper around SNAP's radiometric calibration

    This function takes OST imported Sentinel-1 product and generates
    it to calibrated backscatter.

    3 different calibration modes are supported.
        - Radiometrically terrain corrected Gamma nought (RTC)
          NOTE: that the routine actually calibrates to bet0 and needs to
          be used together with _terrain_flattening routine
        - ellipsoid based Gamma nought (GTCgamma)
        - Sigma nought (GTCsigma).

    Args:
        infile: string or os.path object for
                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
        outfile: string or os.path object for the output
                 file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to
        resolution (int): the resolution of the output product in meters
        product_type (str): the product type of the output product
                            i.e. RTC, GTCgamma or GTCsigma

    '''

    # get gpt file
    gpt_file = h.gpt_path()

    # get path to graph
    rootpath = importlib.util.find_spec('ost').submodule_search_locations[0]

    if product_type == 'RTC':
        print(' INFO: Calibrating the product to a RTC product.')
        graph = opj(rootpath, 'graphs', 'S1_SLC2ARD',
                    'S1_SLC_TNR_Calbeta_Deb.xml')
    elif product_type == 'GTCgamma':
        print(' INFO: Calibrating the product to a GTC product (Gamma0).')
        graph = opj(rootpath, 'graphs', 'S1_SLC2ARD',
                    'S1_SLC_TNR_CalGamma_Deb.xml')
    elif product_type == 'GTCsigma':
        print(' INFO: Calibrating the product to a GTC product (Sigma0).')
        graph = opj(rootpath, 'graphs', 'S1_SLC2ARD',
                    'S1_SLC_TNR_CalSigma_Deb.xml')
    else:
        print(' ERROR: Wrong product type selected.')
        sys.exit(121)

    print(" INFO: Removing thermal noise, calibrating and debursting")
    command = '{} {} -x -q {} -Pinput={} -Poutput={}' \
        .format(gpt_file, graph, 2 * os.cpu_count(), infile, outfile)

    return_code = h.run_command(command, logfile)

    if return_code == 0:
        print(' INFO: Succesfully calibrated product')
    else:
        print(' ERROR: Frame import exited with an error. \
                See {} for Snap Error output'.format(logfile))
        # sys.exit(121)

    return return_code


def _terrain_flattening(infile, outfile, logfile, dem_dict):
    '''A wrapper around SNAP's terrain flattening

    This function takes OST calibrated Sentinel-1 SLC product and applies
    the terrain flattening to correct for radiometric distortions along slopes

    Args:
        infile: string or os.path object for
                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
        outfile: string or os.path object for the output
                 file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to

    '''

    # get gpt file
    gpt_file = h.gpt_path()

    print(' INFO: Correcting for the illumination along slopes'
          ' (Terrain Flattening).'
    )

    command = ('{} Terrain-Flattening -x -q {} '
               ' -PadditionalOverlap=0.15'
               ' -PoversamplingMultiple=1.5'
               ' -PdemName=\'{}\''
               ' -PexternalDEMFile=\'{}\''
               ' -PexternalDEMNoDataValue=\'{}\''
               ' -PdemResamplingMethod=\'{}\''
               ' -t {} {}'.format(
                   gpt_file, 2 * os.cpu_count(), 
                   dem_dict['dem name'], dem_dict['dem file'], 
                   dem_dict['dem nodata'], dem_dict['dem resampling'],
                   outfile, infile)
    )
    
    return_code = h.run_command(command, logfile)

    if return_code == 0:
        print(' INFO: Succesfully applied the terrain flattening.')
    else:
        print(' ERROR: Terrain Flattening exited with an error.'
              ' See {} for Snap Error output'.format(logfile)
        )
        
    return return_code


def _speckle_filter(infile, outfile, logfile):
    '''A wrapper around SNAP's Lee-Sigma Speckle Filter

    This function takes OST imported Sentinel-1 product and applies
    a standardised version of the Lee-Sigma Speckle Filter with
    SNAP's defaut values.

    Args:
        infile: string or os.path object for
                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
        outfile: string or os.path object for the output
                 file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to
    '''

    # get path to SNAP's command line executable gpt
    gpt_file = h.gpt_path()

    print(' INFO: Applying the Lee-Sigma Speckle Filter')
    # contrcut command string
    command = '{} Speckle-Filter -x -q {} -PestimateENL=true \
              -t \'{}\' \'{}\''.format(gpt_file, 2 * os.cpu_count(),
                                       outfile, infile)

    # run command and get return code
    return_code = h.run_command(command, logfile)

    # hadle errors and logs
    if return_code == 0:
        print(' INFO: Succesfully speckle-filtered product')
    else:
        print(' ERROR: Speckle Filtering exited with an error. \
                See {} for Snap Error output'.format(logfile))
        # sys.exit(111)

    return return_code


def _linear_to_db(infile, outfile, logfile):
    '''A wrapper around SNAP's linear to db routine

    This function takes an OST calibrated Sentinel-1 product
    and converts it to dB.

    Args:
        infile: string or os.path object for
                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
        outfile: string or os.path object for the output
                 file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to
    '''

    # get path to SNAP's command line executable gpt
    gpt_file = h.gpt_path()

    print(' INFO: Converting the image to dB-scale.')
    # construct command string
    command = '{} LinearToFromdB -x -q {} -t \'{}\' {}'.format(
        gpt_file, 2 * os.cpu_count(), outfile, infile)

    # run command and get return code
    return_code = h.run_command(command, logfile)

    # handle errors and logs
    if return_code == 0:
        print(' INFO: Succesfully converted product to dB-scale.')
    else:
        print(' ERROR: Linear to dB conversion exited with an error. \
                See {} for Snap Error output'.format(logfile))
        # sys.exit(113)
    return return_code


def _ls_mask(infile, outfile, logfile, resolution, dem_dict):
    '''A wrapper around SNAP's Layover/Shadow mask routine

    This function takes OST imported Sentinel-1 product and calculates
    the Layover/Shadow mask.

    Args:
        infile: string or os.path object for
                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
        outfile: string or os.path object for the output
                 file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to
        resolution (int): the resolution of the output product in meters
        dem (str): A Snap compliant string for the dem to use.
                   Possible choices are:
                       'SRTM 1sec HGT' (default)
                       'SRTM 3sec'
                       'ASTER 1sec GDEM'
                       'ACE30'

    '''

    # get gpt file
    gpt_file = h.gpt_path()

    # get path to graph
    rootpath = importlib.util.find_spec('ost').submodule_search_locations[0]
    graph = opj(rootpath, 'graphs', 'S1_SLC2ARD', 'S1_SLC_LS_TC.xml')

    print(" INFO: Compute Layover/Shadow mask")
    command = ('{} {} -x -q {}'
               ' -Pinput={}'
               ' -Presol={}'
               ' -Pdem=\'{}\'' 
               ' -Pdem_file=\'{}\''
               ' -Pdem_nodata=\'{}\'' 
               ' -Pdem_resampling=\'{}\''
               ' -Pimage_resampling=\'{}\''
               ' -Poutput={}'.format(
                   gpt_file, graph, 2 * os.cpu_count(), infile, resolution,
                   dem_dict['dem name'], dem_dict['dem file'], 
                   dem_dict['dem nodata'], dem_dict['dem resampling'], 
                   dem_dict['image resampling'],
                   outfile)
    )

    return_code = h.run_command(command, logfile)

    if return_code == 0:
        print(' INFO: Succesfully created Layover/Shadow mask')
    else:
        print(' ERROR: Layover/Shadow mask creation exited with an error. \
                See {} for Snap Error output'.format(logfile))
        # sys.exit(121)

    return return_code


#def _coreg(filelist, outfile, logfile, dem_dict):
#    '''A wrapper around SNAP's back-geocoding co-registration routine
#
#    This function takes a list of 2 OST imported Sentinel-1 SLC products
#    and co-registers them properly. This routine is sufficient for coherence
#    estimation, but not for InSAR, since the ESD refinement is not applied.
#
#    Args:
#        infile: string or os.path object for
#                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
#        outfile: string or os.path object for the output
#                 file written in BEAM-Dimap format
#        logfile: string or os.path object for the file
#                 where SNAP'S STDOUT/STDERR is written to
#        dem (str): A Snap compliant string for the dem to use.
#                   Possible choices are:
#                       'SRTM 1sec HGT' (default)
#                       'SRTM 3sec'
#                       'ASTER 1sec GDEM'
#                       'ACE30'
#
#    '''
#
#    # get gpt file
#    gpt_file = h.gpt_path()
#
#    # get path to graph
#    rootpath = importlib.util.find_spec('ost').submodule_search_locations[0]
#    graph = opj(rootpath, 'graphs', 'S1_SLC2ARD', 'S1_SLC_BGD.xml')
#
#    print(' INFO: Co-registering {}'.format(filelist[0]))
#    command = '{} {} -x -q {} -Pfilelist={} -Poutput={} -Pdem=\'{}\''\
#        .format(gpt_file, graph, 2 * os.cpu_count(), filelist, outfile, dem)
#
#    return_code = h.run_command(command, logfile)
#
#    if return_code == 0:
#        print(' INFO: Succesfully coregistered product.')
#    else:
#        print(' ERROR: Co-registration exited with an error. \
#                See {} for Snap Error output'.format(logfile))
#        # sys.exit(112)
#
#    return return_code


def _coreg2(master, slave,  outfile, logfile, dem_dict):
    '''A wrapper around SNAP's back-geocoding co-registration routine

    This function takes a list of 2 OST imported Sentinel-1 SLC products
    and co-registers them properly. This routine is sufficient for coherence
    estimation, but not for InSAR, since the ESD refinement is not applied.

    Args:
        infile: string or os.path object for
                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
        outfile: string or os.path object for the output
                 file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to
        dem (str): A Snap compliant string for the dem to use.
                   Possible choices are:
                       'SRTM 1sec HGT' (default)
                       'SRTM 3sec'
                       'ASTER 1sec GDEM'
                       'ACE30'

    '''

    # get gpt file
    gpt_file = h.gpt_path()

    # get path to graph
    rootpath = importlib.util.find_spec('ost').submodule_search_locations[0]
    graph = opj(rootpath, 'graphs', 'S1_SLC2ARD', 'S1_SLC_Coreg.xml')

    print(' INFO: Co-registering {} and {}'.format(master, slave))
    command = ('{} {} -x -q {} '
                ' -Pmaster={}'
                ' -Pslave={}'
                ' -Pdem=\'{}\'' 
                ' -Pdem_file=\'{}\''
                ' -Pdem_nodata=\'{}\'' 
                ' -Pdem_resampling=\'{}\''
                ' -Poutput={} '.format(
                    gpt_file, graph, 2 * os.cpu_count(), 
                    master, slave,
                    dem_dict['dem name'], dem_dict['dem file'], 
                    dem_dict['dem nodata'], dem_dict['dem resampling'], 
                    outfile)
    )

    return_code = h.run_command(command, logfile)

    if return_code == 0:
        print(' INFO: Succesfully coregistered product.')
    else:
        print(' ERROR: Co-registration exited with an error. \
                See {} for Snap Error output'.format(logfile))

    return return_code


def _coherence(infile, outfile, logfile, polar='VV,VH,HH,HV'):
    '''A wrapper around SNAP's coherence routine

    This function takes a co-registered stack of 2 Sentinel-1 SLC products
    and calculates the coherence.

    Args:
        infile: string or os.path object for
                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
        outfile: string or os.path object for the output
                 file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to

    '''

    # get gpt file
    gpt_file = h.gpt_path()

    # get path to graph
    rootpath = importlib.util.find_spec('ost').submodule_search_locations[0]
    graph = opj(rootpath, 'graphs', 'S1_SLC2ARD', 'S1_SLC_Coh_Deb.xml')

    print(' INFO: Coherence estimation')
    command = '{} {} -x -q {} -Pinput={} -Ppolar=\'{}\' -Poutput={}' \
        .format(gpt_file, graph, 2 * os.cpu_count(), infile, polar, outfile)

    return_code = h.run_command(command, logfile)

    if return_code == 0:
        print(' INFO: Succesfully created coherence product.')
    else:
        print(' ERROR: Coherence exited with an error. \
                See {} for Snap Error output'.format(logfile))

    return return_code


def _terrain_correction(infile, outfile, logfile, resolution, dem_dict):
    '''A wrapper around SNAP's Terrain Correction routine

    This function takes an OST calibrated Sentinel-1 product and
    does the geocodification.

    Args:
        infile: string or os.path object for
                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
        outfile: string or os.path object for the output
                 file written in BEAM-Dimap format
        logfile: string or os.path object for the file
                 where SNAP'S STDOUT/STDERR is written to
        resolution (int): the resolution of the output product in meters
        dem (str): A Snap compliant string for the dem to use.
                   Possible choices are:
                       'SRTM 1sec HGT' (default)
                       'SRTM 3sec'
                       'ASTER 1sec GDEM'
                       'ACE30'

    '''

    # get gpt file
    gpt_file = h.gpt_path()

    print(" INFO: Geocoding input scene")

    command = ('{} Terrain-Correction -x -q {}'
                   ' -PdemName=\'{}\''
                   ' -PexternalDEMFile=\'{}\''
                   ' -PexternalDEMNoDataValue=\'{}\''  
                   ' -PdemResamplingMethod=\'{}\''
                   ' -PimgResamplingMethod=\'{}\''
                   ' -PnodataValueAtSea=\'false\''
                   ' -PpixelSpacingInMeter=\'{}\''
                   ' -t {} {}'.format(
                       gpt_file, 2 * os.cpu_count(), 
                       dem_dict['dem name'], dem_dict['dem file'], 
                       dem_dict['dem nodata'], dem_dict['dem resampling'], 
                       dem_dict['image resampling'],
                       resolution, outfile, infile)
    )

    return_code = h.run_command(command, logfile)

    if return_code == 0:
        print(' INFO: Succesfully orthorectified product.')
    else:
        print(' ERROR: Geocoding exited with an error. \
                See {} for Snap Error output'.format(logfile))

    return return_code


#def _terrain_correction_deg(infile, outfile, logfile, resolution=0.001,
#                            dem='SRTM 1sec HGT'):
#    '''A wrapper around SNAP's Terrain Correction routine
#
#    This function takes an OST calibrated Sentinel-1 product and
#    does the geocodification.
#
#    Args:
#        infile: string or os.path object for
#                an OST imported frame in BEAM-Dimap format (i.e. *.dim)
#        outfile: string or os.path object for the output
#                 file written in BEAM-Dimap format
#        logfile: string or os.path object for the file
#                 where SNAP'S STDOUT/STDERR is written to
#        resolution (int): the resolution of the output product in degree
#        dem (str): A Snap compliant string for the dem to use.
#                   Possible choices are:
#                       'SRTM 1sec HGT' (default)
#                       'SRTM 3sec'
#                       'ASTER 1sec GDEM'
#                       'ACE30'
#
#    '''
#
#    # get gpt file
#    gpt_file = h.gpt_path()
#
#    print(" INFO: Geocoding input scene")
#    command = '{} Terrain-Correction -x -q {} \
#              -PdemResamplingMethod=\'BILINEAR_INTERPOLATION\' \
#              -PimgResamplingMethod=\'BILINEAR_INTERPOLATION\' \
#              -PnodataValueAtSea=\'false\' \
#              -PpixelSpacingInDegree=\'{}\' \
#              -PdemName=\'{}\' \
#              -t {} {}' \
#              .format(gpt_file, 2 * os.cpu_count(), resolution, dem,
#                      outfile, infile)
#
#    return_code = h.run_command(command, logfile)
#
#    if return_code == 0:
#        print(' INFO: Succesfully orthorectified product.')
#    else:
#        print(' ERROR: Geocoding exited with an error. \
#                See {} for Snap Error output'.format(logfile))
#
#    return return_code


def burst_to_ard(master_file,
                 swath,
                 master_burst_nr,
                 master_burst_id,
                 proc_file,
                 out_dir,
                 temp_dir,
                 slave_file=None,
                 slave_burst_nr=None,
                 slave_burst_id=None,
                 coherence=False,
                 remove_slave_import=False):
    '''The main routine to turn a burst into an ARD product

    Args:
        master_file (str): path to full master SLC scene
        swath (str): subswath
        master_burst_nr (): index number of the burst
        master_burst_id ():
        out_dir (str):
        temp_dir (str):
        slave_file (str):
        slave_burst_nr (str):
        slave_burst_id (str):
        proc_file (str):
        remove_slave_import (bool):

    '''

    # load ards
    with open(proc_file, 'r') as ard_file:
        ard_params = json.load(ard_file)['processing parameters']
        ard = ard_params['single ARD']
        
    # import master
    master_import = opj(temp_dir, '{}_import'.format(master_burst_id))

    if not os.path.exists('{}.dim'.format(master_import)):
        import_log = opj(out_dir, '{}_import.err_log'.format(master_burst_id))
        polars = ard['polarisation'].replace(' ', '')
        return_code = _import(master_file, master_import, import_log,
                              swath, master_burst_nr, polars)
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

    if ard['H-A-Alpha']:
        # create HAalpha file
        out_haa = opj(temp_dir, '{}_h'.format(master_burst_id))
        haa_log = opj(out_dir, '{}_haa.err_log'.format(
            master_burst_id))
        return_code = _ha_alpha('{}.dim'.format(master_import),
                                out_haa, haa_log, ard['remove pol speckle'])

        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # geo code HAalpha
        out_htc = opj(temp_dir, '{}_pol'.format(master_burst_id))
        haa_tc_log = opj(out_dir, '{}_haa_tc.err_log'.format(
            master_burst_id))
        return_code = _terrain_correction(
            '{}.dim'.format(out_haa), out_htc, haa_tc_log, 
            ard['resolution'], ard['dem'])

        # last check on the output files
        return_code = h.check_out_dimap(out_htc)
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # move to final destination
        h.move_dimap(
            out_htc, opj(out_dir, '{}_pol'.format(master_burst_id)))

        # remove HAalpha tmp files
        h.delete_dimap(out_haa)

    # calibrate
    out_cal = opj(temp_dir, '{}_cal'.format(master_burst_id))
    cal_log = opj(out_dir, '{}_cal.err_log'.format(master_burst_id))
    return_code = _calibration(
        '{}.dim'.format(master_import), out_cal, cal_log, ard['product type'])
    if return_code != 0:
        h.remove_folder_content(temp_dir)
        return return_code

    if not coherence:
        #  remove imports
        h.delete_dimap(master_import)

    # speckle filtering
    if ard['remove speckle']:
        speckle_import = opj(temp_dir, '{}_speckle_import'.format(
            master_burst_id))
        speckle_log = opj(out_dir, '{}_speckle.err_log'.format(
            master_burst_id))
        return_code = _speckle_filter('{}.dim'.format(out_cal),
                                      speckle_import, speckle_log)
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # remove temp file
        h.delete_dimap(out_cal)

        # reset master_import for follwoing routine
        out_cal = speckle_import

    # do terrain flattening in case it is selected
    if ard['product type'] == 'RTC':
        # define outfile
        out_rtc = opj(temp_dir, '{}_rtc'.format(master_burst_id))
        rtc_log = opj(out_dir, '{}_rtc.err_log'.format(
            master_burst_id))
        # do the TF
        return_code = _terrain_flattening('{}.dim'.format(out_cal),
                                          out_rtc, rtc_log, ard['dem'])
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # remove tmp files
        h.delete_dimap(out_cal)
        # set out_rtc to out_cal for further processing
        out_cal = out_rtc

    if ard['to db']:
        out_db = opj(temp_dir, '{}_cal_db'.format(master_burst_id))
        db_log = opj(out_dir, '{}_cal_db.err_log'.format(master_burst_id))
        return_code = _linear_to_db('{}.dim'.format(out_cal), out_db, db_log)
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # remove tmp files
        h.delete_dimap(out_cal)
        # set out_cal to out_db for further processing
        out_cal = out_db

    # geo code backscatter products
    out_tc = opj(temp_dir, '{}_bs'.format(master_burst_id))
    tc_log = opj(out_dir, '{}_bs_tc.err_log'.format(master_burst_id))
    return_code = _terrain_correction(
        '{}.dim'.format(out_cal), out_tc, tc_log, ard['resolution'], ard['dem'])

    # last check on backscatter data
    return_code = h.check_out_dimap(out_tc)
    if return_code != 0:
        h.remove_folder_content(temp_dir)
        return return_code

    # we move backscatter to final destination
    h.move_dimap(out_tc, opj(out_dir, '{}_bs'.format(master_burst_id)))

    if ard['create ls mask']:
        # create LS map
        out_ls = opj(temp_dir, '{}_LS'.format(master_burst_id))
        ls_log = opj(out_dir, '{}_LS.err_log'.format(master_burst_id))
        return_code = _ls_mask('{}.dim'.format(out_cal), out_ls, ls_log,
                               ard['resolution'], ard['dem'])
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # last check on ls data
        return_code = h.check_out_dimap(out_ls, test_stats=False)
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # move ls data to final destination
        h.move_dimap(out_ls, opj(out_dir, '{}_LS'.format(master_burst_id)))

    # remove calibrated files
    h.delete_dimap(out_cal)

    if coherence:

        # import slave
        slave_import = opj(temp_dir, '{}_import'.format(slave_burst_id))
        import_log = opj(out_dir, '{}_import.err_log'.format(slave_burst_id))
        polars = ard['polarisation'].replace(' ', '')
        return_code = _import(slave_file, slave_import, import_log,
                              swath, slave_burst_nr, polars)

        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # co-registration
        #filelist = ['{}.dim'.format(master_import),
        #            '{}.dim'.format(slave_import)]
        #filelist = '\'{}\''.format(','.join(filelist))
        out_coreg = opj(temp_dir, '{}_coreg'.format(master_burst_id))
        coreg_log = opj(out_dir, '{}_coreg.err_log'.format(master_burst_id))
        # return_code = _coreg(filelist, out_coreg, coreg_log, dem)
        return_code = _coreg2('{}.dim'.format(master_import),
                              '{}.dim'.format(slave_import),
                               out_coreg,
                               coreg_log, ard['dem'])
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        #  remove imports
        h.delete_dimap(master_import)

        if remove_slave_import is True:
            h.delete_dimap(slave_import)

        # calculate coherence and deburst
        out_coh = opj(temp_dir, '{}_c'.format(master_burst_id))
        coh_log = opj(out_dir, '{}_coh.err_log'.format(master_burst_id))
        coh_polars = ard['coherence bands'].replace(' ', '')
        return_code = _coherence('{}.dim'.format(out_coreg),
                                 out_coh, coh_log, coh_polars)
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # remove coreg tmp files
        h.delete_dimap(out_coreg)

        # geocode
        out_tc = opj(temp_dir, '{}_coh'.format(master_burst_id))
        tc_log = opj(out_dir, '{}_coh_tc.err_log'.format(master_burst_id))
        return_code = _terrain_correction(
            '{}.dim'.format(out_coh), out_tc, tc_log, 
            ard['resolution'], ard['dem'])
        
        # last check on coherence data
        return_code = h.check_out_dimap(out_tc)
        if return_code != 0:
            h.remove_folder_content(temp_dir)
            return return_code

        # move to final destination
        h.move_dimap(out_tc, opj(out_dir, '{}_coh'.format(master_burst_id)))

        # remove tmp files
        h.delete_dimap(out_coh)

    # write file, so we know this burst has been succesfully processed
    if return_code == 0:
        check_file = opj(out_dir, '.processed')
        with open(str(check_file), 'w') as file:
            file.write('passed all tests \n')
    else:
        h.remove_folder_content(temp_dir)
        h.remove_folder_content(out_dir)

    return return_code


if __name__ == "__main__":

    import argparse

    # write a description
    descript = """
               This is a command line client for the creation of
               Sentinel-1 ARD data from Level 1 SLC bursts

               to do
               """

    epilog = """
             Example:
             to do


             """


    # create a parser
    parser = argparse.ArgumentParser(description=descript, epilog=epilog)

    # search paramenters
    parser.add_argument('-m', '--master',
                        help=' (str) path to the master SLC',
                        required=True)
    parser.add_argument('-ms', '--master_swath',
                        help=' (str) The subswath of the master SLC',
                        required=True)
    parser.add_argument('-mn', '--master_burst_nr',
                        help=' (int) The index number of the master burst',
                        required=True)
    parser.add_argument('-mi', '--master_burst_id',
                        help=' (str) The OST burst id of the master burst')
    parser.add_argument('-o', '--out_directory',
                        help='The directory where the outputfiles will'
                             ' be written to.',
                        required=True)
    parser.add_argument('-t', '--temp_directory',
                        help='The directory where temporary files will'
                             ' be written to.',
                        required=True)
    parser.add_argument('-s', '--slave',
                        help=' (str) path to the slave SLC',
                        default=False)
    parser.add_argument('-sn', '--slave_burst_nr',
                        help=' (int) The index number of the slave burst',
                        default=False)
    parser.add_argument('-si', '--slave_burst_id',
                        help=' (str) The OST burst id of the slave burst',
                        default=False)
    parser.add_argument('-c', '--coherence',
                        help=' (bool) Set to True if the interferometric '
                        'coherence should be calculated.',
                        default=False)
    parser.add_argument('-p', '--proc_file',
                        help=' (str/path) Path to ARDprocessing parameters file',
                        required=True)
    parser.add_argument('-rsi', '--remove_slave_import',
                        help=' (bool) Select if during the coherence'
                             ' calculation the imported slave file should be'
                             ' deleted (for time-series it is advisable to'
                             ' keep it)',
                        default=False)

    args = parser.parse_args()

    # execute processing
    burst_to_ard(args.master, args.master_swath, args.master_burst_nr, 
                 args.master_burst_id, args.proc_file, args.out_directory, args.temp_directory,
                 args.slave, args.slave_burst_nr, args.slave_burst_id,
                 args.coherence, args.remove_slave_import)
