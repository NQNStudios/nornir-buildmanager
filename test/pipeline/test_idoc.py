'''
Created on Feb 13, 2013

@author: u0490822
'''
import glob
import logging
import os
import shutil
import time
import unittest

from nornir_buildmanager.VolumeManagerETree import VolumeManager 
import nornir_buildmanager.importers
from nornir_buildmanager.importers.serialemlog import SerialEMLog
from nornir_imageregistration.files.mosaicfile import MosaicFile
import nornir_shared.files
import nornir_shared.misc

import nornir_buildmanager.build as build
import nornir_buildmanager.importers.serialemlog as serialemlog
import nornir_buildmanager.importers.idoc as idoc
from . import setup_pipeline


class IDocTest(setup_pipeline.PlatformTest):

    @property
    def classname(self):
        clsstr = str(self.__class__.__name__)
        return clsstr

    @property
    def VolumePath(self):
        return "RC2_4Square"

    @property
    def Platform(self):
        return "IDoc"
    
    @property
    def Grid32ManualStosFullPath(self):
        return os.path.join(self.PlatformFullPath, "IDocBuildTest_Grid32Manual")


class StosRebuildHelper(object):
    
    @property
    def Grid32ManualStosFullPath(self):
        return os.path.join(self.PlatformFullPath, "IDocBuildTest_Grid32Manual")
      
    def FetchStosTransformsByInputTransformChecksum(self, input_transform_list, stos_group_name):
        '''Find all of the transforms from a stos group with a matching path'''
          
        volumeObj = self.LoadVolume()
        stosGroup = volumeObj.find("Block/StosGroup[@Name='%s']" % stos_group_name)
        self.assertIsNotNone(stosGroup, "Stos group not found %s" % (stos_group_name))
          
        outputTransformList = []
        for originalTransform in input_transform_list:
            updatedTransform = stosGroup.find("SectionMappings/Transform[@InputTransformChecksum='%s']" % (originalTransform.Checksum))
            self.assertIsNotNone(updatedTransform, "No transform found with input transform checksum %s" % originalTransform.Checksum)
              
            outputTransformList.append(updatedTransform)
          
        return outputTransformList
    
    
    def FetchMosaicToVolumeTransformsByInputTransformChecksum(self, input_transform_list):
        '''Find all of the transforms from a stos group with a matching path'''
          
        volumeObj = self.LoadVolume()
        stosBlock = volumeObj.find("Block")
        self.assertIsNotNone(stosBlock, "Stos block not found %s")
          
        outputTransformList = []
        for originalTransform in input_transform_list:
            updatedTransform = stosBlock.find("Section/Channel/Transform[@InputTransformChecksum='%s']" % (originalTransform.Checksum))
            self.assertIsNotNone(updatedTransform, "No transform found with input transform checksum %s" % originalTransform.Checksum)
              
            outputTransformList.append(updatedTransform)
          
        return outputTransformList
    
    
    def FetchMosaicToVolumeTransforms(self, input_transform_list):
        '''Find all of the transforms from a stos group with a matching path'''
          
        volume_obj = self.LoadVolume() 
          
        outputTransformList = []
        for originalTransform in input_transform_list:
            updatedTransform = self._FetchMosaicToVolumeTransform(volume_obj, originalTransform)
            outputTransformList.append(updatedTransform)
          
        return outputTransformList
    
    def _FetchMosaicToVolumeTransform(self, volume_obj, input_transform):
 
        stosBlock = volume_obj.find("Block")
        self.assertIsNotNone(stosBlock, "Stos block not found %s")
        
        section_number = input_transform.FindParent('Section').Number
        channel_name = input_transform.FindParent('Channel').Name
         
        updatedTransform = stosBlock.find("Section[@Number='%d']/Channel[@Name='%s']/Transform[@Name='%s']" % (int(section_number), channel_name, input_transform.Name))
        self.assertIsNotNone(updatedTransform, "No transform found with input transform checksum %s" % input_transform.InputTransform)
        
        return updatedTransform
      
      
    def ForceStosRebuild(self, Grid32ManualStosFullPath, BruteLevel):
        '''Add a manual transform to the grid32 level.  Ensure the entire stack is regenerated'''
          
        StosGroupName = 'Grid32'
        
          
        # OK, part two is to change a mosaic, and ensure that every file downstream is updated
        transformList = self.CopyManualStosFiles(Grid32ManualStosFullPath, StosGroupName=StosGroupName)
        self.assertGreater(len(transformList), 0, "Transform list should not be empty")

        grid32TransformList = self.RunPipelineToRefreshStosGroupTransforms(transformList,
                                                     stos_group_name='Grid32',
                                                     func=self.RunRefineSectionAlignment,
                                                     func_args_dict={
                                                     'InputGroup':"StosBrute",
                                                     'InputLevel':BruteLevel,
                                                     'OutputGroup':"Grid",
                                                     'OutputLevel':BruteLevel,
                                                     'Filter':"Leveled"}
                                                     )

        originalGrid8TransformList = self.FetchStosTransformsByInputTransformChecksum(transformList, stos_group_name="Grid8")
        self.assertGreater(len(originalGrid8TransformList), 0, "Transform list should not be empty")
          
        grid8TransformList = self.RunPipelineToRefreshStosGroupTransforms(originalGrid8TransformList,
                                                     stos_group_name='Grid8',
                                                     func=self.RunRefineSectionAlignment,
                                                     func_args_dict={
                                                     'InputGroup':"Grid",
                                                     'InputLevel':BruteLevel,
                                                     'OutputGroup':"Grid",
                                                     'OutputLevel':BruteLevel / 4,
                                                     'Filter':"Leveled"}
                                                     )
          
        originalGrid1TransformList = self.FetchStosTransformsByInputTransformChecksum(originalGrid8TransformList, stos_group_name="Grid1")
        self.assertGreater(len(originalGrid1TransformList), 0, "Transform list should not be empty")
           
        grid1TransformList = self.RunPipelineToRefreshStosGroupTransforms(originalGrid1TransformList,
                                                     stos_group_name='Grid1',
                                                     func=self.RunScaleVolumeTransforms,
                                                     func_args_dict={
                                                     'InputGroup':"Grid",
                                                     'InputLevel':BruteLevel / 4,
                                                     'OutputLevel': 1}
                                                     )
          
        originalsliceToVolume1TransformList = self.FetchStosTransformsByInputTransformChecksum(originalGrid1TransformList, stos_group_name="SliceToVolume1")
        self.assertGreater(len(originalsliceToVolume1TransformList), 0, "Transform list should not be empty")
          
        sliceToVolume1 = self.RunPipelineToRefreshStosGroupTransforms(originalsliceToVolume1TransformList,
                                                     stos_group_name='SliceToVolume1',
                                                     func=self.RunSliceToVolume,
                                                     func_args_dict={})
        
        originalChannelToMosaicUntranslatedTransformList = self.FetchMosaicToVolumeTransformsByInputTransformChecksum(originalsliceToVolume1TransformList)
        self.assertGreater(len(originalChannelToMosaicUntranslatedTransformList), 0, "Transform list should not be empty")
        
        originalChannelToMosaicTransformList = self.FetchMosaicToVolumeTransformsByInputTransformChecksum(originalChannelToMosaicUntranslatedTransformList)
        self.assertGreater(len(originalChannelToMosaicTransformList), 0, "Transform list should not be empty")
        
        
                   
        sliceToVolume1 = self.RunPipelineToRefreshChannelToMosaicTransforms(originalChannelToMosaicUntranslatedTransformList,
                                                                            originalChannelToMosaicTransformList,
                                                                            func=self.RunMosaicToVolume,
                                                                            func_args_dict={})
        
         
          
    def RunPipelineToRefreshStosGroupTransforms(self, transformList, stos_group_name, func, func_args_dict):
        '''Run a pipeline that should update every transform in the transform list.
           Returns the updated transforms'''
          
        full_transform_paths = setup_pipeline.FullPathsForNodes(transformList)
        last_modified_dict = setup_pipeline.BuildPathToModifiedDateMap(full_transform_paths)
           
        updatedVolumeObj = func(**func_args_dict)

        return self._EnsureStosGroupTransformsRefreshed(volumeObj=updatedVolumeObj,
                                               stos_group_name=stos_group_name,
                                               originalTransformList=transformList,
                                               last_modified_dict=last_modified_dict)
          
    def _EnsureStosGroupTransformsRefreshed(self, volumeObj, stos_group_name, originalTransformList, last_modified_dict):
        '''Given a list of transforms, ensure that each transform has been updated'''
                  
        stosGroup = volumeObj.find("Block/StosGroup[@Name='%s']" % stos_group_name)
        self.assertIsNotNone(stosGroup, "Stos group not found %s" % (stos_group_name))
          
        updatedTransforms = []
        for originalTransform in originalTransformList:
            updatedTransform = stosGroup.find("SectionMappings/Transform[@Path='%s']" % (originalTransform.Path))
            self.assertIsNotNone(updatedTransform, "Updated transform is None, should match manual transform info")
              
            # All files should be replaced with the manual stos files
            self.VerifyFilesLastModifiedDateChanged(last_modified_dict)
              
            self.assertNotEqual(updatedTransform.Checksum, originalTransform.Checksum, "Checksums should not match after being replaced by a manual stos file")
              
            updatedTransforms.append(updatedTransform)
              
        return updatedTransforms
    
    def RunPipelineToRefreshChannelToMosaicTransforms(self, transform_untranslated_list, transform_translated_list, func, func_args_dict):
        '''Run a pipeline that should update every transform in the transform list.
           Returns the updated transforms'''
          
        full_untranslated_transform_paths = setup_pipeline.FullPathsForNodes(transform_untranslated_list)
        last_untranslated_modified_dict = setup_pipeline.BuildPathToModifiedDateMap(full_untranslated_transform_paths)
        
        full_translated_transform_paths = setup_pipeline.FullPathsForNodes(transform_translated_list)
        last_translated_modified_dict = setup_pipeline.BuildPathToModifiedDateMap(full_translated_transform_paths)
           
        updatedVolumeObj = func(**func_args_dict)
        
        self._EnsureChannelToMosaicTransformsRefreshed(volumeObj=updatedVolumeObj,
                                                              originalTransformList=transform_untranslated_list,
                                                              last_modified_dict=last_untranslated_modified_dict)
        
        return self._EnsureChannelToMosaicTransformsRefreshed(volumeObj=updatedVolumeObj,
                                                              originalTransformList=transform_translated_list,
                                                              last_modified_dict=last_translated_modified_dict)
          
         
        
    def _EnsureChannelToMosaicTransformsRefreshed(self, volumeObj, originalTransformList, last_modified_dict):
         
          
        updatedTransforms = []
        for originalTransform in originalTransformList:
            updatedTransform = self._FetchMosaicToVolumeTransform(volumeObj, originalTransform)
              
            # All files should be replaced with the manual stos files
            self.VerifyFilesLastModifiedDateChanged(last_modified_dict)
              
            self.assertNotEqual(updatedTransform.Checksum, originalTransform.Checksum, "Checksums should not match after being replaced by a manual stos file")
              
            updatedTransforms.append(updatedTransform)
              
        return updatedTransforms
      
          
          

class IDocSingleSectionImportTest(IDocTest):

    @property
    def VolumePath(self):
        return "RC2_Micro\\%d" % self.SectionNumber

    @property
    def SectionNumber(self):
        return 17
    
    @property
    def HistogramFullPath(self):
        return os.path.join(self.ImportedDataPath, nornir_buildmanager.importers.DefaultHistogramFilename)

    def LoadMetaData(self):
        '''Updates the object's meta-data variables from disk'''

        # Load the meta-data from the volumedata.xml file
        self.VolumeObj = VolumeManager.Load(self.TestOutputPath)

        self.ChannelData = self.VolumeObj.find("Block/Section[@Number='17']/Channel")
        self.assertIsNotNone(self.ChannelData, "Could not locate channel meta-data")
        self.RawFilterObj = self._getRawDataFilterNode(self.SectionNumber)

        # OK, by default the transforms should be correct
        self.StageTransform = self.ChannelData.GetChildByAttrib('Transform', 'Name', 'Stage')
#        self.PruneTransform = self.ChannelData.GetChildByAttrib('Transform', 'Name', 'Prune')
#        self.TranslateTransform = self.ChannelData.GetChildByAttrib('Transform', 'Name', 'Translate')
        self.GridTransform = self.ChannelData.GetChildByAttrib('Transform', 'Name', 'Grid')
#        self.ZeroGridTransform = self.ChannelData.GetChildByAttrib('Transform', 'Name', 'ZeroGrid')

        self.assertIsNotNone(self.StageTransform)
#        self.assertIsNotNone(self.PruneTransform)
#        self.assertIsNotNone(self.TranslateTransform)
#        self.assertIsNotNone(self.GridTransform)
#        self.assertIsNotNone(self.ZeroGridTransform)

    @property
    def Block(self):
        block = self.VolumeObj.find('Block')
        self.assertIsNotNone(block)
        return block
    

    def _getRawDataFilterNode(self, SectionNumber):
        SectionNode = self.Block.GetSection(SectionNumber)
        self.assertIsNotNone(SectionNode)

        ChannelNode = SectionNode.GetChannel('TEM')
        self.assertIsNotNone(ChannelNode)

        FilterNode = ChannelNode.GetFilter('Raw8')
        self.assertIsNotNone(FilterNode)

        return FilterNode
    
    def CreateImportContrastOverrideMapping(self, sectionNumber, MinVal, MaxVal, Gamma):
        ContrastMap = {}        
        ContrastMap[sectionNumber] = nornir_buildmanager.importers.ContrastValues(sectionNumber, MinVal, MaxVal, Gamma)
        return ContrastMap 
    
    def VerifyFilterContrast(self, MinVal, MaxVal, Gamma):
        FilterObj = self._getRawDataFilterNode(self.SectionNumber)
        self.assertIsNotNone(FilterObj)
        
        self.assertFalse(FilterObj.IsContrastMismatched(MinVal, MaxVal, Gamma))

    def runTest(self):
         
        self.RunImport()
        self.LoadMetaData()

        SectionNodes = list(self.VolumeObj.findall("Block/Section"))
        self.assertEqual(len(SectionNodes), 1)
        
        
        IDocData = self.ChannelData.GetChildByAttrib('Data', 'Name', 'IDoc')
        self.assertIsNotNone(IDocData)

        LogData = self.ChannelData.GetChildByAttrib('Data', 'Name', 'Log')
        self.assertIsNotNone(LogData)

        BlockNode = self.VolumeObj.find('Block')
        self.assertIsNotNone(BlockNode)
        
        FilterObj = self._getRawDataFilterNode(self.SectionNumber)
        self.assertIsNotNone(FilterObj)
        
        OriginalMaxIntensity = FilterObj.MaxIntensityCutoff
        OriginalMinIntensity = FilterObj.MinIntensityCutoff
        OriginalGamma = FilterObj.Gamma
        
        TargetMinIntensity = 1500
        TargetMaxIntensity = 6000
        TargetGamma = 1.0
        
        ContrastMap = self.CreateImportContrastOverrideMapping(self.SectionNumber, TargetMinIntensity, TargetMaxIntensity, Gamma=TargetGamma)

        # Make sure we have images and mosaics for the original imported data.  We want to make sure these are regenerated after the second import.
        self.RunHistogram(Transform='Stage')
        self.LoadMetaData() 
        
        # histogramNode = self.RawFilterObj.GetHistogram()
        # self.assertFalse(histogramNode.IsContrastMismatched(OriginalMinIntensity, OriginalMaxIntensity, OriginalGamma))
        self.RunAdjustContrast(Transform='Stage')
        
        # I do not run mosaic based on the prune transform both to save time and to ensure that rebuilding the prune transform is not rebuilding the mosaic and images by some side-effect
        self.RunMosaic(Filter='Leveled', Transform='Stage')
        self.LoadMetaData()
        
        # self.assertFalse(self.RawFilterObj.TilePyramid.IsContrastMismatched(OriginalMinIntensity, OriginalMaxIntensity, OriginalGamma))
        # self.assertFalse(self.RawFilterObj.Imageset.IsContrastMismatched(OriginalMinIntensity, OriginalMaxIntensity, OriginalGamma))         
        self.EnsureTilePyramidIsFull(self.RawFilterObj, 25)

        self.RunSetFilterLocked(str(self.SectionNumber), Channels="TEM", Filters="Raw8", Locked="1")
        
        
        nornir_buildmanager.importers.SaveHistogramCutoffs(self.HistogramFullPath, ContrastMap)
        
        self.RunImport()
        self.LoadMetaData()
        self.VerifyFilterContrast(OriginalMinIntensity, OriginalMaxIntensity, OriginalGamma)
        
        self.RunSetFilterLocked(str(self.SectionNumber), Channels="TEM", Filters="Raw8", Locked="0")
        
        self.RunImport()
        self.LoadMetaData() 
        self.VerifyFilterContrast(TargetMinIntensity, TargetMaxIntensity, Gamma=TargetGamma)
        
        # Check that the histogram has the new target values
        self.RunHistogram(Transform='Stage')
        self.LoadMetaData()
        # self.assertFalse(self.RawFilterObj.GetHistogram().IsContrastMismatched(TargetMinIntensity, TargetMaxIntensity, TargetGamma))
        
        self.RunAdjustContrast(Transform='Stage')
        self.RunMosaic(Filter='Leveled', Transform='Stage')
        
        self.LoadMetaData() 
        # self.assertFalse(self.RawFilterObj.Imageset.IsContrastMismatched(TargetMinIntensity, TargetMaxIntensity, TargetGamma)) 
        
        
        
    def tearDown(self):
        IDocTest.tearDown(self)
        if os.path.exists(self.HistogramFullPath):
            os.remove(self.HistogramFullPath)
          
 
class IDocAlignOutputTest(setup_pipeline.CopySetupTestBase):
    '''Attemps an alignment on a cached copy of the output from IDocBuildTest'''
 
    @property
    def VolumePath(self):
        return "RC2_4Square_Aligned"
 
    @property
    def Platform(self):
        return "IDOC"
 
    def runTest(self):
        # Doesn't need to run if IDocBuildTest is run, here for debugging convienience if it fails
 
        BruteLevel = 32
        self.RunScaleVolumeTransforms(InputGroup="Grid", InputLevel=BruteLevel / 4, OutputLevel=1)
        self.RunSliceToVolume()
        self.RunMosaicToVolume()
        self.RunCreateVikingXML("SliceToVolume")
        self.RunAssembleMosaicToVolume(Channels="TEM")
      
#     
class IDocBuildTest(IDocTest, StosRebuildHelper):
             
    def runTest(self):
              
        self.RunImport()
        self.RunPrune()
              
        self.RunSetPruneCutoff(Value="7.5", Section="693", Channels="*", Filters="Raw8")
              
        self.RunHistogram()
              
        self.RunSetContrast(MinValue="125", MaxValue="NaN", GammaValue="NaN", Section="693", Channels="*", Filters="Raw8")
              
        self.RunAdjustContrast()
              
        self.RemoveAndRegenerateTile(RegenFunction=self.RunAdjustContrast, RegenKwargs={'Sections' : 691}, section_number=691, channel='TEM', filter_name='Leveled', level=1)
        self.RemoveAndRegenerateTile(RegenFunction=self.RunAdjustContrast, RegenKwargs={'Sections' : 691}, section_number=691, channel='TEM', filter_name='Leveled', level=2)  
        self.RemoveAndRegenerateTile(RegenFunction=self.RunAdjustContrast, RegenKwargs={'Sections' : 691}, section_number=691, channel='TEM', filter_name='Leveled', level=4)       
                      
        self.RunSetFilterLocked('693', Channels="TEM", Filters="Leveled", Locked="1")
        self.RunSetFilterLocked('693', Channels="TEM", Filters="Leveled", Locked="0")
              
        self.RunMosaic(Filter="Leveled")
        self.RunMosaicReport()
        self.RunAssemble(Channels='TEM', Levels=[8, 16])
                      
        self.RunCreateVikingXML(StosGroup=None, StosMap=None, OutputFile="Mosaic")
        self.RunMosaicReport()
              
        # Copy output here to run IDocAlignTest
              
        BruteLevel = 32
              
        self.RunCreateBlobFilter(Channels="TEM", Filter="Leveled", Levels="8,16,%d" % (BruteLevel))
        self.RunAlignSections(Channels="TEM", Filters="Blob", Levels=BruteLevel, Center=693)
                      
        self.RunAssembleStosOverlays(Group="StosBrute", Downsample=BruteLevel, StosMap='PotentialRegistrationChain')
        self.RunSelectBestRegistrationChain(Group="StosBrute", Downsample=BruteLevel, InputStosMap='PotentialRegistrationChain', OutputStosMap='FinalStosMap')
                      
        self.RunRefineSectionAlignment(InputGroup="StosBrute", InputLevel=BruteLevel, OutputGroup="Grid", OutputLevel=BruteLevel, Filter="Leveled")
        self.RunRefineSectionAlignment(InputGroup="Grid", InputLevel=BruteLevel, OutputGroup="Grid", OutputLevel=BruteLevel / 4, Filter="Leveled")
              
        # Copy output here to run IDocAlignOutputTest
              
        self.RunScaleVolumeTransforms(InputGroup="Grid", InputLevel=BruteLevel / 4, OutputLevel=1)
        self.RunSliceToVolume()
        self.RunMosaicToVolume()
        self.RunCreateVikingXML(StosGroup='SliceToVolume1', StosMap='SliceToVolume', OutputFile="SliceToVolume")
        self.RunAssembleMosaicToVolume(Channels="TEM")
        self.RunMosaicReport(OutputFile='VolumeReport')
        self.RunExportImages(Channels="Registered", Filters="Leveled", AssembleLevel=16)
     
        self.RunAssemble(Channels='TEM', Levels=[1])
        self.RunExportImages(Channels="TEM", Filters="Leveled", AssembleLevel=1, Output="MosaicExport")
          
        # TODO, this failed.  Fix it
        self.ForceStosRebuild(self.Grid32ManualStosFullPath, BruteLevel)
  
        self.RunCalculateStosGroupWarpMetrics() 
# 
# # # #
# class IDocBuildTestBootstrapDebugging(setup_pipeline.CopySetupTestBase, StosRebuildHelper):
# # 
#     @property
#     def VolumePath(self):
#         return "IDocBuildTest"
#           
#     @property
#     def Platform(self):
#         return "Temp" 
#       
#     @property
#     def Grid32ManualStosFullPath(self):
#         return os.path.join(self.PlatformFullPath, "IDocBuildTest_Grid32Manual")
#       
#    def runTest(self):
#         self.RunImport()
#         self.RunPrune()
#             
#         self.RunSetPruneCutoff(Value="7.5", Section="693", Channels="*", Filters="Raw8")
#             
#         self.RunHistogram()
#             
#         self.RunSetContrast(MinValue="125", MaxValue="NaN", GammaValue="NaN", Section="693", Channels="*", Filters="Raw8")
#             
#         self.RunAdjustContrast()
#             
#         self.RemoveAndRegenerateTile(RegenFunction=self.RunAdjustContrast, RegenKwargs={'Sections' : 691}, section_number=691, channel='TEM', filter='Leveled', level=1)
#         self.RemoveAndRegenerateTile(RegenFunction=self.RunAdjustContrast, RegenKwargs={'Sections' : 691}, section_number=691, channel='TEM', filter='Leveled', level=2)  
#         self.RemoveAndRegenerateTile(RegenFunction=self.RunAdjustContrast, RegenKwargs={'Sections' : 691}, section_number=691, channel='TEM', filter='Leveled', level=4)       
#                     
#         self.RunSetFilterLocked('693', Channels="TEM", Filters="Leveled", Locked="1")
#         self.RunSetFilterLocked('693', Channels="TEM", Filters="Leveled", Locked="0")
# #           
#         self.RunMosaic(Filter="Leveled")
#         self.RunMosaicReport()
#         self.RunAssemble(Channels='TEM', Levels=[8, 16])
#                     
#         self.RunCreateVikingXML(StosGroup=None, StosMap=None, OutputFile="Mosaic")
#         self.RunMosaicReport()
#            
# #        Copy output here to run IDocAlignTest
#            
#        BruteLevel = 32
#            
#         self.RunCreateBlobFilter(Channels="TEM", Filter="Leveled", Levels="8,16,%d" % (BruteLevel))
#         self.RunAlignSections(Channels="TEM", Filters="Blob", Levels=BruteLevel, Center=693)
#                    
#         self.RunAssembleStosOverlays(Group="StosBrute", Downsample=BruteLevel, StosMap='PotentialRegistrationChain')
#         self.RunSelectBestRegistrationChain(Group="StosBrute", Downsample=BruteLevel, InputStosMap='PotentialRegistrationChain', OutputStosMap='FinalStosMap')
#                    
#         self.RunRefineSectionAlignment(InputGroup="StosBrute", InputLevel=BruteLevel, OutputGroup="Grid", OutputLevel=BruteLevel, Filter="Leveled")
#         self.RunRefineSectionAlignment(InputGroup="Grid", InputLevel=BruteLevel, OutputGroup="Grid", OutputLevel=BruteLevel / 4, Filter="Leveled")
#            
#         # Copy output here to run IDocAlignOutputTest
#            
#         self.RunScaleVolumeTransforms(InputGroup="Grid", InputLevel=BruteLevel / 4, OutputLevel=1)
#         self.RunSliceToVolume()
#         self.RunMosaicToVolume()
#         self.RunCreateVikingXML(StosGroup='SliceToVolume1', StosMap='SliceToVolume', OutputFile="SliceToVolume")
#         self.RunAssembleMosaicToVolume(Channels="TEM")
#         self.RunMosaicReport(OutputFile='VolumeReport')
#         self.RunExportImages(Channels="Registered", Filters="Leveled", AssembleLevel=16)
#          
#         self.RunAssemble(Channels='TEM', Levels=[1])
#         self.RunExportImages(Channels="TEM", Filters="Leveled", AssembleLevel=1, Output="MosaicExport")
#          
#         # TODO, this failed.  Fix it
#         self.ForceStosRebuild(self.Grid32ManualStosFullPath, BruteLevel)
#         
#         
#         self.RunCalculateStosGroupWarpMetrics()
#          
# #           
#            
#===============================================================================
#  
# class IDocAlignTest(setup_pipeline.CopySetupTestBase):
#     '''Attemps an alignment on a cached copy of the output from IDocBuildTest'''
#  
#     @property
#     def VolumePath(self):
#         return "IDocAlignTest"
#  
#     @property
#     def Platform(self):
#         return "IDOC"
#  
#     def runTest(self):
#         # Doesn't need to run if IDocBuildTest is run, here for debugging convienience if it fails
#         # return
#         BruteLevel = 32
#           
#         self.RunRefineSectionAlignment(InputGroup="Grid", InputLevel=BruteLevel, OutputGroup="Grid", OutputLevel=BruteLevel / 4, Filter="Leveled")
#         self.RunScaleVolumeTransforms(InputGroup="Grid", InputLevel=BruteLevel / 4, OutputLevel=1)
#         self.RunSliceToVolume()
#         self.RunMosaicToVolume() 
#         self.RunCreateVikingXML(StosGroup='SliceToVolume1', StosMap='SliceToVolume', OutputFile="SliceToVolume")
#         self.RunAssembleMosaicToVolume(Channels="TEM")
#         self.RunMosaicReport(OutputFile='VolumeReport')
#         self.RunExportImages(Channels="Registered", Filters="Leveled", AssembleLevel=16) 
#===============================================================================

class IdocReaderTest(IDocTest):

    @property
    def VolumePath(self):
        return "RC2_Micro"

    def runTest(self):
        NumLogTiles = 25

        idocDir = os.path.join(self.ImportedDataPath, '17/*.idoc')
        idocFiles = glob.glob(idocDir)

        self.assertEqual(len(idocFiles), 1, "Idoc file not found")

        idocFile = idocFiles[0]
        self.assertTrue(os.path.exists(idocFile))

        IDocData = idoc.IDoc.Load(idocFile)

        self.assertEqual(IDocData.ImageSeries, 1)
        self.assertEqual(IDocData.PixelSpacing, 21.76)
        self.assertEqual(IDocData.ImageSize, [4080, 4080])
        self.assertEqual(IDocData.Montage, 1)
        self.assertEqual(IDocData.DataMode, 1)

        self.assertEqual(len(IDocData.tiles), NumLogTiles, "Incorrect number of tiles found in log, expected " + str(NumLogTiles) + ", got " + str(len(IDocData.tiles)))

        # From the log file we see that the tile wtih Z=6 should have a drift of 0.69 nm/sec
        TileData = IDocData.tiles[5]
        self.assertIsNotNone(TileData)
        self.assertEqual(TileData.Image, '10005.tif')
        self.assertEqual(TileData.Magnification, 5000)
        self.assertEqual(TileData.Intensity, 0.549157)
        self.assertEqual(TileData.SpotSize, 2)
        self.assertEqual(TileData.ExposureTime, 0.75)
        self.assertEqual(TileData.RotationAngle , -178.3)
        self.assertEqual(TileData.Defocus , -6.8902)
        self.assertEqual(TileData.PieceCoordinates, [3590, 7180, 0])
        return

class LogReaderTest(IDocTest):

    @property
    def VolumePath(self):
        return "RC2_Micro"

    def validateLogEntries(self, LogData):
        NumLogTiles = 25

        self.assertEqual(LogData.Version, "3.1.1a,  built Nov  9 2011  14:20:16")
        self.assertEqual(LogData.Startup, "4/22/2012  16:03:59")
        self.assertEqual(LogData.PropertiesVersion, "Sep 30, 2011")
        self.assertEqual(LogData.MontageStart, 4719.609)
        self.assertEqual(LogData.MontageEnd, 5467.422)

        self.assertEqual(len(LogData.tileData), NumLogTiles, "Incorrect number of tiles found in log, expected " + str(NumLogTiles) + ", got " + str(len(LogData.tileData)))

        # From the log file we see that the tile wtih Z=6 should have a drift of 0.69 nm/sec
        TileData = LogData.tileData[6]
        self.assertIsNotNone(TileData)
        self.assertEqual(TileData.drift, 0.69)
        self.assertEqual(TileData.driftUnits, "nm/sec")
        self.assertEqual(len(TileData.driftStamps), 1)
        self.assertEqual(TileData.startTime, 4924.937)
        self.assertEqual(TileData.endTime, 4948.016)

        # From the log file we see that the tile wtih Z=22 should have two recorded drifts, 1.38, 0.9
        TileData = LogData.tileData[23]
        self.assertIsNotNone(TileData)
        self.assertEqual(TileData.drift, 0.9)
        self.assertEqual(TileData.driftUnits, "nm/sec")
        self.assertEqual(len(TileData.driftStamps), 2)
        self.assertEqual(TileData.stageStopTime, 5409.531)

        self.assertEqual(TileData.driftStamps[0], (5412.5 - TileData.stageStopTime, 1.38))
        self.assertEqual(TileData.driftStamps[1], (5423.234 - TileData.stageStopTime, 0.9))

        self.assertEqual(TileData.startTime, 5402.328)
        self.assertEqual(TileData.endTime, 5433.453)

    def runTest(self):
        logDir = os.path.join(self.ImportedDataPath, '17/*.log')
        logFiles = glob.glob(logDir)

        self.assertEqual(len(logFiles), 1)

        logFile = logFiles[0]
        self.assertTrue(os.path.exists(logFile))

        LogData = SerialEMLog.Load(logFile, usecache=False)
        self.validateLogEntries(LogData)

        cachedLogData = SerialEMLog.Load(logFile, usecache=True)
        self.validateLogEntries(cachedLogData)

        outputGrid = os.path.join(self.TestOutputPath, 'Grid_' + os.path.basename(logFile) + '.png')
        outputDrift = os.path.join(self.TestOutputPath, 'Drift_' + os.path.basename(logFile) + '.png')

        serialemlog.PlotDriftGrid(cachedLogData, outputGrid)
        serialemlog.PlotDriftSettleTime(cachedLogData, outputDrift)
        return

if __name__ == "__main__":
    # import syssys.argv = ['', 'Test.testName']
    unittest.main()
