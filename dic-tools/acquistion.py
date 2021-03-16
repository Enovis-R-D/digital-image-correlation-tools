# ============================================================================
# Copyright (c) 2001-2019 FLIR Systems, Inc. All Rights Reserved.

# This software is the confidential and proprietary information of FLIR
# Integrated Imaging Solutions, Inc. ("Confidential Information"). You
# shall not disclose such Confidential Information and shall use it only in
# accordance with the terms of the license agreement you entered into
# with FLIR Integrated Imaging Solutions, Inc. (FLIR).
#
# FLIR MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF THE
# SOFTWARE, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, OR NON-INFRINGEMENT. FLIR SHALL NOT BE LIABLE FOR ANY DAMAGES
# SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR DISTRIBUTING
# THIS SOFTWARE OR ITS DERIVATIVES.
# ============================================================================
#
# AcquisitionMultipleCamera.py shows how to capture images from
# multiple cameras simultaneously. It relies on information provided in the
# Enumeration, Acquisition, and NodeMapInfo examples.
#
# This example reads similarly to the Acquisition example,
# except that loops are used to allow for simultaneous acquisitions.

import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
import PySpin
import sys
from datetime import datetime as dt
import os
import contextlib
from pathlib import Path
from loguru import logger
from collections import namedtuple

trigger_type = namedtuple('Triggers', 'software hardware')
triggers = trigger_type(1, 2)
selected_trigger = triggers.software


def configure_trigger(cam):
    """
    This function configures the camera to use a trigger. First, trigger mode is
    set to off in order to select the trigger source. Once the trigger source
    has been selected, trigger mode is then enabled, which has the camera
    capture only a single image upon the execution of the chosen trigger.

     :param cam: Camera to configure trigger for.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """
    result = True

    logger.info('*** CONFIGURING TRIGGER ***\n')
    if selected_trigger == triggers.software:
        logger.info('Software trigger chosen ...')
    elif selected_trigger == triggers.hardware:
        logger.info('Hardware trigger chose ...')
    try:
        # Ensure trigger mode off
        # The trigger must be disabled in order to configure whether the source
        # is software or hardware.
        nodemap = cam.GetNodeMap()
        node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
        if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
            logger.error('Unable to disable trigger mode (node retrieval). Aborting...')
            return False

        node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
        if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
            logger.error('Unable to disable trigger mode (enum entry retrieval). Aborting...')
            return False
        node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())
        logger.info('Trigger mode disabled...')

        # Set TriggerSelector to FrameStart
        # For this example, the trigger selector should be set to frame start.
        # This is the default for most cameras.
        node_trigger_selector = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSelector'))
        if not PySpin.IsAvailable(node_trigger_selector) or not PySpin.IsWritable(node_trigger_selector):
            logger.error('Unable to get trigger selector (node retrieval). Aborting...')
            return False

        node_trigger_selector_framestart = node_trigger_selector.GetEntryByName('FrameStart')
        if not PySpin.IsAvailable(node_trigger_selector_framestart) or not PySpin.IsReadable(
                node_trigger_selector_framestart):
            logger.error('Unable to set trigger selector (enum entry retrieval). Aborting...')
            return False
        node_trigger_selector.SetIntValue(node_trigger_selector_framestart.GetValue())

        logger.info('Trigger selector set to frame start...')

        # Select trigger source
        # The trigger source must be set to hardware or software while trigger
        # mode is off.
        node_trigger_source = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSource'))
        if not PySpin.IsAvailable(node_trigger_source) or not PySpin.IsWritable(node_trigger_source):
            logger.error('Unable to get trigger source (node retrieval). Aborting...')
            return False

        if selected_trigger == triggers.software:
            node_trigger_source_software = node_trigger_source.GetEntryByName('Software')
            if not PySpin.IsAvailable(node_trigger_source_software) or not PySpin.IsReadable(
                    node_trigger_source_software):
                logger.error('Unable to set trigger source (enum entry retrieval). Aborting...')
                return False
            node_trigger_source.SetIntValue(node_trigger_source_software.GetValue())
            logger.info('Trigger source set to software...')

        elif selected_trigger == triggers.hardware:
            node_trigger_source_hardware = node_trigger_source.GetEntryByName('Line0')
            if not PySpin.IsAvailable(node_trigger_source_hardware) or not PySpin.IsReadable(
                    node_trigger_source_hardware):
                logger.error('Unable to set trigger source (enum entry retrieval). Aborting...')
                return False
            node_trigger_source.SetIntValue(node_trigger_source_hardware.GetValue())
            logger.info('Trigger source set to hardware...')

        # Turn trigger mode on
        # Once the appropriate trigger source has been set, turn trigger mode
        # on in order to retrieve images using the trigger.
        node_trigger_mode_on = node_trigger_mode.GetEntryByName('On')
        if not PySpin.IsAvailable(node_trigger_mode_on) or not PySpin.IsReadable(node_trigger_mode_on):
            logger.error('Unable to enable trigger mode (enum entry retrieval). Aborting...')
            return False

        node_trigger_mode.SetIntValue(node_trigger_mode_on.GetValue())
        logger.info('Trigger mode turned back on...')

    except PySpin.SpinnakerException as ex:
        logger.error('Error: %s' % ex)
        return False

    return result


def execute_trigger(nodemap):
    """
    This function acquires an image by executing the trigger node.

    :param nodemap: Device nodemap.
    :type nodemap: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True
        # Use trigger to capture image
        # The software trigger only feigns being executed by the Enter key;
        # what might not be immediately apparent is that there is not a
        # continuous stream of images being captured; in other examples that
        # acquire images, the camera captures a continuous stream of images.
        # When an image is retrieved, it is plucked from the stream.

        if selected_trigger == triggers.software:
            # Execute software trigger
            node_softwaretrigger_cmd = PySpin.CCommandPtr(nodemap.GetNode('TriggerSoftware'))
            if not PySpin.IsAvailable(node_softwaretrigger_cmd) or not PySpin.IsWritable(node_softwaretrigger_cmd):
                print('Unable to execute trigger. Aborting...')
                return False

            node_softwaretrigger_cmd.Execute()

            # TODO: Blackfly and Flea3 GEV cameras need 2 second delay after software trigger

        elif selected_trigger == triggers.hardware:
            print('Use the hardware to trigger image acquisition.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def reset_trigger(nodemap):
    """
    This function returns the camera to a normal state by turning off trigger mode.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True
        node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
        if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
            print('Unable to disable trigger mode (node retrieval). Aborting...')
            return False

        node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
        if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
            print('Unable to disable trigger mode (enum entry retrieval). Aborting...')
            return False

        node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())

        print('Trigger mode disabled...')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


# this script pauses before each image is taken and waits for the user to press a key
NUM_IMAGES = 10  # number of images to grab
# todo update save_directory to where you want images saved.
# This hasn't been tested yet. Files may just save in folder with python script
save_directory = Path(r'C:\Users\Npyle1\OneDrive - DJO LLC\Pictures\DIC\testing')


def acquire_images(cam_list):
    """
    This function acquires and saves images from each device.

    :param cam_list: List of cameras
    :type cam_list: CameraList
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    logger.info('*** IMAGE ACQUISITION ***\n')
    try:
        result = True

        # Prepare each camera to acquire images
        #
        # *** NOTES ***
        # For pseudo-simultaneous streaming, each camera is prepared as if it
        # were just one, but in a loop. Notice that cameras are selected with
        # an index. We demonstrate pseduo-simultaneous streaming because true
        # simultaneous streaming would require multiple process or threads,
        # which is too complex for an example.
        #

        for i, cam in enumerate(cam_list):

            # Set acquisition mode to continuous
            node_acquisition_mode = PySpin.CEnumerationPtr(cam.GetNodeMap().GetNode('AcquisitionMode'))
            if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
                logger.error('Unable to set acquisition mode to continuous (node retrieval; camera %d). Aborting... \n' % i)
                return False
            node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
            if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                    node_acquisition_mode_continuous):
                logger.error('Unable to set acquisition mode to continuous (entry \'continuous\' retrieval %d). \
                Aborting... \n' % i)
                return False
            acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
            node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
            logger.info('Camera %d acquisition mode set to continuous...' % i)
            # Set StreamBuferHandlingMode to NewestOnly
            s_node_map = cam.GetTLStreamNodeMap()
            node_buffer_handling_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
            if not PySpin.IsAvailable(node_buffer_handling_mode) or not PySpin.IsWritable(node_buffer_handling_mode):
                logger.error('Unable to set buffer mode to newest only (node retrieval; camera %d). Aborting... \n' % i)
                return False
            node_buffer_handling_mode_newest = node_buffer_handling_mode.GetEntryByName('NewestOnly')
            if not PySpin.IsAvailable(node_buffer_handling_mode_newest) or not PySpin.IsReadable(
                    node_buffer_handling_mode_newest):
                logger.error('Unable to set buffer mode to newest only (entry \'continuous\' retrieval %d). \
                Aborting... \n' % i)
                return False
            buffer_handling_newest = node_buffer_handling_mode_newest.GetValue()
            node_buffer_handling_mode.SetIntValue(buffer_handling_newest)
            logger.info('Camera %d buffer handling mode set to newest only' % i)
            # set trigger to software trigger
            configure_trigger(cam)
            # todo set pixel format (mono8?)

            # Begin acquiring images
            cam.BeginAcquisition()
            logger.info('Camera %d started acquiring images...' % i)

        # Retrieve, convert, and save images for each camera
        #
        # *** NOTES ***
        # In order to work with simultaneous camera streams, nested loops are
        # needed. It is important that the inner loop be the one iterating
        # through the cameras; otherwise, all images will be grabbed from a
        # single camera before grabbing any images from another.
        for n in range(NUM_IMAGES):
            # Get user input
            input('Press any key to initiate software trigger./n')
            # trigger cameras close together
            for i, cam in enumerate(cam_list):
                nodemap = cam.GetNodeMap()
                execute_trigger(nodemap)
            for i, cam in enumerate(cam_list):

                try:
                    # Retrieve device serial number for filename
                    node_device_serial_number = PySpin.CStringPtr(
                        cam.GetTLDeviceNodeMap().GetNode('DeviceSerialNumber'))
                    if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
                        device_serial_number = node_device_serial_number.GetValue()
                        logger.info('Camera %d serial number set to %s...' % (i, device_serial_number))
                    else:
                        device_serial_number = False
                    # Retrieve next received image and ensure image completion
                    image_result = cam.GetNextImage()
                    if image_result.IsIncomplete():
                        logger.warning('Image incomplete with image status %d ... \n' % image_result.GetImageStatus())
                    else:
                        # Print image information
                        width = image_result.GetWidth()
                        height = image_result.GetHeight()
                        logger.info('Camera %d grabbed image %d, width = %d, height = %d' % (i, n, width, height))
                        # Convert image to mono 8
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
                        # Create a unique filename
                        if device_serial_number:
                            filename = 'AcquisitionMultipleCamera-%s-%d-%s.jpg' % (
                                device_serial_number, n, str(dt.now()).replace(":", "").replace(".", ""))
                        else:
                            filename = 'AcquisitionMultipleCamera-%d-%d.jpg' % (i, n)
                        # Save image
                        image_converted.Save(filename)
                        logger.info('Image saved at %s' % filename)

                    # Release image
                    image_result.Release()

                except PySpin.SpinnakerException as ex:
                    logger.error('Error: %s' % ex)
                    result = False

        # End acquisition for each camera
        #
        # *** NOTES ***
        # Notice that what is usually a one-step process is now two steps
        # because of the additional step of selecting the camera. It is worth
        # repeating that camera selection needs to be done once per loop.
        #
        # It is possible to interact with cameras through the camera list with
        # GetByIndex(); this is an alternative to retrieving cameras as
        # CameraPtr objects that can be quick and easy for small tasks.
        for cam in cam_list:
            nodemap = cam.GetNodeMap()
            reset_trigger(nodemap)
            # End acquisition
            cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        logger.error('Error: %s' % ex)
        result = False

    return result


def print_device_info(nodemap, cam_num):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :param cam_num: Camera number.
    :type nodemap: INodeMap
    :type cam_num: int
    :returns: True if successful, False otherwise.
    :rtype: bool
    """

    logger.info('Printing device information for camera %d... \n' % cam_num)

    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                logger.info('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            logger.error('Device control information not available.')

    except PySpin.SpinnakerException as ex:
        logger.error('Error: %s' % ex)
        return False

    return result


def run_multiple_cameras(cam_list):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam_list: List of cameras
    :type cam_list: CameraList
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Retrieve transport layer nodemaps and print device information for
        # each camera
        # *** NOTES ***
        # This example retrieves information from the transport layer nodemap
        # twice: once to print device information and once to grab the device
        # serial number. Rather than caching the nodem#ap, each nodemap is
        # retrieved both times as needed.
        logger.info('*** DEVICE INFORMATION ***\n')

        for i, cam in enumerate(cam_list):
            # Retrieve TL device nodemap
            nodemap_tldevice = cam.GetTLDeviceNodeMap()

            # Print device information
            result &= print_device_info(nodemap_tldevice, i)

        # Initialize each camera
        #
        # *** NOTES ***
        # You may notice that the steps in this function have more loops with
        # less steps per loop; this contrasts the AcquireImages() function
        # which has less loops but more steps per loop. This is done for
        # demonstrative purposes as both work equally well.
        #
        # *** LATER ***
        # Each camera needs to be deinitialized once all images have been
        # acquired.
        for i, cam in enumerate(cam_list):
            # Initialize camera
            cam.Init()

        # Acquire images on all cameras
        result &= acquire_images(cam_list)

        # Deinitialize each camera
        #
        # *** NOTES ***
        # Again, each camera must be deinitialized separately by first
        # selecting the camera and then deinitializing it.
        for cam in cam_list:
            # Deinitialize camera
            cam.DeInit()

        # Release reference to camera
        # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
        # cleaned up when going out of scope.
        # The usage of del is preferred to assigning the variable to None.
        del cam

    except PySpin.SpinnakerException as ex:
        logger.error('Error: %s' % ex)
        result = False

    return result


def main():
    """
    Example entry point; please see Enumeration example for more in-depth
    comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """

    # Since this application saves images in the current folder
    # we must ensure that we have permission to write to this folder.
    # If we do not have permission, fail right away.
    try:
        test_file = open('test.txt', 'w+')
    except IOError:
        logger.error('Unable to write to current directory. Please check permissions.')
        # input('Press Enter to exit...')
        return False

    test_file.close()
    os.remove(test_file.name)

    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    # version = system.GetLibraryVersion()
    # logger.debug('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    logger.info('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:
        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        logger.warning('Not enough cameras!')
        # input('Done! Press Enter to exit...')
        return False

    # Run example on all cameras
    logger.info('Running example for all cameras...')

    result = run_multiple_cameras(cam_list)

    # Clear camera list before releasing system
    cam_list.Clear()
    # Release system instance
    system.ReleaseInstance()

    logger.success('Done!')
    return result


if __name__ == '__main__':
    with working_directory(save_directory):
        if main():
            sys.exit(0)
        else:
            sys.exit(1)
