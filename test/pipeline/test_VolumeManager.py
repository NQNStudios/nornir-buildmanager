'''
Created on Feb 18, 2013

@author: u0490822
'''
import unittest
import unittest
import nornir_buildmanager.importers.pmg as pmg
import os
import shutil
import glob
import logging

import nornir_shared.misc
import nornir_shared.files

from nornir_buildmanager.VolumeManagerETree import *


class VolumeManagerTest(unittest.TestCase):

    def setUp(self):
        nornir_shared.misc.SetupLogging(os.path.join(os.getcwd(), "test_volumemanager"));

        self.VolumeFullPath = os.path.join(os.getcwd(), "test/data/TestOutput/test_volumemanager");

        if os.path.exists(self.VolumeFullPath):
            shutil.rmtree(self.VolumeFullPath);

        self.VolumeObj = VolumeManager.Load(self.VolumeFullPath, Create = True);


    def tearDown(self):
        if os.path.exists(self.VolumeFullPath):
            shutil.rmtree(self.VolumeFullPath);

class VolumeManagerAppendTest(VolumeManagerTest):

    def runTest(self):

        logger = logging.getLogger("VMAppendTest");
        self.assertEqual(self.VolumeObj.tag, "Volume");

        # Try adding a block, first as a
        BlockObj = BlockNode(Name = 'Block', Path = 'Block');
        [added, BlockObj] = self.VolumeObj.UpdateOrAddChild(BlockObj);

        self.assertTrue(added);
        self.assertTrue(BlockObj in self.VolumeObj);

        imageObj = ImageNode("Some.png");
        [added, imageObj] = BlockObj.UpdateOrAddChild(imageObj);
        self.assertTrue(imageObj in BlockObj);
    #
        dataObj = DataNode("Some.xml");
        [added, dataObj] = BlockObj.UpdateOrAddChild(dataObj);
        self.assertTrue(dataObj in BlockObj);

        tnode = TransformNode(Name = "Stage", Path = "SomePath.mosaic", Checksum = "ABCDE", Type = 'Test');
        BlockObj.UpdateOrAddChild(tnode);
        self.assertTrue(tnode in BlockObj);

        HistogramElement = HistogramNode(tnode, Type = 'Test', attrib = None);
        [HistogramElementCreated, HistogramElement] = BlockObj.UpdateOrAddChildByAttrib(HistogramElement, "Type");

        c = HistogramElement.__class__;
        self.assertTrue(HistogramElement in BlockObj);

    #    ImageNode = VolumeManagerETree.XElementWrapper('Image', {'path' : OutputHistogramPngFilename});
    #    [added, ImageNode] = HistogramElement.UpdateOrAddChild(ImageNode);
    #
    #    DataNode = VolumeManagerETree.XElementWrapper('Data', {'Path' : OutputHistogramXmlFilename});
    #    [added, DataNode] = HistogramElement.UpdateOrAddChild(DataNode);
        imageObj = ImageNode("Histogram.png");
        [added, imageObj] = HistogramElement.UpdateOrAddChild(imageObj);
        self.assertTrue(imageObj in HistogramElement);


    #
        dataObj = DataNode("Histogram.xml");
        [added, dataObj] = HistogramElement.UpdateOrAddChild(dataObj);
        self.assertTrue(dataObj in HistogramElement);

        p = dataObj.FullPath;
        s = str(dataObj);
        t = str(HistogramElement);

        for k in HistogramElement.attrib.keys():
            v = HistogramElement.attrib[k];
            print str(v);

        d = HistogramElement.DataNode;

        self.assertTrue(dataObj in HistogramElement);

        HistogramElement.Clean();

        self.VolumeObj.Save();




if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()