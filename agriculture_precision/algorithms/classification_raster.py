# -*- coding: utf-8 -*-

"""
/***************************************************************************
 AgriculturePrecision
                                 A QGIS plugin
 Chaines de traitement
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-07-21
        copyright            : (C) 2020 by ASPEXIT
        email                : cleroux@aspexit.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'ASPEXIT'
__date__ = '2020-07-21'
__copyright__ = '(C) 2020 by ASPEXIT'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

#import QColor

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsApplication,
                       QgsRasterLayer,
                       #QgsColorRampShader,
                       #QgsRasterShader,
                       #QgsSingleBandPseudoColorRenderer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterEnum)

from .functions.fonctions_repartition import *

from qgis import processing 

from osgeo import gdal
import numpy as np
#from PyQt5.QtGui import QColor

class ClassifyRaster(QgsProcessingAlgorithm):
    """
    
    """

    OUTPUT= 'OUTPUT'
    INPUT = 'INPUT'
    INPUT_METHOD = 'INPUT_METHOD'
    INPUT_N_CLASS='INPUT_N_CLASS'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                self.tr('Couche raster a traiter')
            )
        )

       
        self.addParameter(
            QgsProcessingParameterEnum(
                self.INPUT_METHOD,
                self.tr('Choix de la méthode de classification'),
                ['Quantiles', 'Intervalles Egaux', 'K-means (Iterative Minimum Distance)']                
            )
        )
       
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_N_CLASS, 
                self.tr('Nombre de classes'),
                QgsProcessingParameterNumber.Integer,
                4,
                False,
                2,
                10
            )
        )
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
                self.tr('Classes')
            )
        )
        
        
        

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        
        layer_temp=self.parameterAsRasterLayer(parameters,self.INPUT,context)
        fn = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        method = self.parameterAsEnum(parameters,self.INPUT_METHOD,context)
        nombre_classes=self.parameterAsInt(parameters,self.INPUT_N_CLASS,context)
         
        #k-means
        if method == 2 :
            # K-means clustering for grids
            alg_params = {
                'GRIDS': parameters[self.INPUT],
                'MAXITER': 0,
                'METHOD': 0,
                'NCLUSTER': nombre_classes,
                'NORMALISE': False,
                'OLDVERSION': False,
                'UPDATEVIEW': True,
                'CLUSTER': parameters[self.OUTPUT],
                'STATISTICS': parameters[self.OUTPUT]
            }
            #on place manuellement la couche CLUSTER dans fn, sinon l'algorithme classification n'a pas la couche en OUTPUT (problèmes
            #dans zonage ensuite)
            fn = processing.run('saga:kmeansclusteringforgrids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['CLUSTER']
            
        else :
            # récupération du path de la couche en entrée
            fn_temp = layer_temp.source()
            
            # ouverture de la couche avec la bibliothèque gdal
            ds_temp = gdal.Open(fn_temp)

            #permet de lire la bande du raster en tant que matrice de numpy. 
            band_temp = ds_temp.GetRasterBand(1)
            array = band_temp.ReadAsArray()

            #extraction de la valeur "artificielle" (-infini) des points sans valeur
            nodata_val = band_temp.GetNoDataValue()
            
            #on va masquer les valeurs de "sans valeur", ce qui va permettre le traitement ensuite
            if nodata_val is not None:
                array = np.ma.masked_equal(array, nodata_val)
                
            
            #on créé la couche raster en calque sur la couche source
            driver_tiff = gdal.GetDriverByName("GTiff")
            ds = driver_tiff.Create(fn, xsize=ds_temp.RasterXSize, \
            ysize = ds_temp.RasterYSize, bands = 1, eType = gdal.GDT_Float32)

            ds.SetGeoTransform(ds_temp.GetGeoTransform())
            ds.SetProjection(ds_temp.GetProjection())
            
            #on récupère la bande en matrice
            output = ds.GetRasterBand(1).ReadAsArray()
            
            # on rempli cette couche de NaN
            output[:].fill(np.nan)
         
            #QUANTILES
            if method == 0:             
                output = rep_quantiles(nombre_classes,array,output)
            #INTERVALLES EGAUX
            elif method == 1 :
                output = intervalles_egaux(nombre_classes,array,output)
           
            #JENKS
            #elif method == 2 : 
     
            #ajouter les modifications effectuées sur la matrice dans la couche raster
            ds.GetRasterBand(1).WriteArray(output)
        
        
        ## definir les couleurs du raster
        '''#create the color ramp shader
        fnc = QgsColorRampShader()
        fnc.setColorRampType(QgsColorRampShader.Exact)
        min=0.25
        max=1
        

        #define the color palette (here yellow to green)
        lst = [QgsColorRampShader.ColorRampItem(min, QColor(255,255,102)),QgsColorRampShader.ColorRampItem(0.5, QColor (255,204,51)),QgsColorRampShader.ColorRampItem(0.75, QColor(255,153,51)),QgsColorRampShader.ColorRampItem(max, QColor(255,102,0))]
        fnc.setColorRampItemList(lst)

        #assign the color ramp to a QgsRasterShader so it can be used to symbolize a raster layer.
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(fnc)

        #Apply symbology to raster

        rlayer = QgsRasterLayer(fn)
        renderer = QgsSingleBandPseudoColorRenderer(rlayer.dataProvider(), 1, shader)
        rlayer.setRenderer(renderer)
        '''


        return{self.OUTPUT : fn} 
   
    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "Classification raster"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Action sur Raster')
        
    def shortHelpString(self):
        short_help = self.tr(
            'Permet de reclassifier un raster en un nombre de classes défini par l’utilisateur à l’aide de '
            'plusieurs méthodes de classification : Intervalles égaux, Quantiles, K-means'
        )
        return short_help

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'action_sur_raster'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ClassifyRaster()
