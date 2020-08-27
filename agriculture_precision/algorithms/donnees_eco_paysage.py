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

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsApplication,
                       QgsVectorLayer,
                       QgsDataProvider,
                       QgsVectorDataProvider,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsPointXY,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterField,
                       QgsProcessingParameterBoolean,
                       
                       QgsProcessingUtils,
                       NULL,
                       QgsMessageLog)

from qgis import processing 

import numpy as np
import pandas as pd

class DonneesPaysage(QgsProcessingAlgorithm):
    """
    
    """

    OUTPUT= 'OUTPUT'
    
    INPUT= 'INPUT'
    FIELD_ID = 'FIELD_ID'

   
  

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Vecteur zones'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )

        self.addParameter( 
            QgsProcessingParameterField( 
                self.FIELD_ID,
                self.tr( "Champ identifiant des zones" ), 
                QVariant(),
                self.INPUT
            ) 
        )       
        
        
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Fichier contenant les donnees'),
                '.csv',
            )
        )
        
        

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        
       
        csv = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        zone_id = self.parameterAsString(parameters, self.FIELD_ID, context)
      
        
        alg_params = {
            'CALC_METHOD': 0,
            'INPUT': parameters['INPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        alg_result= processing.run('qgis:exportaddgeometrycolumns', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
        layer = QgsProcessingUtils.mapLayerFromString(alg_result,context)
      
      
        features = layer.getFeatures()
              
        #if parameters[self.BOOLEAN] :
            #liste contenant les noms des champs (uniquement numériques)
        field_list=[field.name() for field in layer.fields() if field.type() in [2,4,6] or field.name() == zone_id] 
            # 4 integer64, 6 Real
       # else :
        #    field_list =[choosed_field, zone_id]
      
        #on créé une matrice ou 1 ligne = 1 feature
        data = np.array([[feat[field_name] for field_name in field_list] for feat in features])
                
        #on créer le dataframe avec les données et les noms des colonnes
        df = pd.DataFrame(data, columns = field_list)
        
        #Remplacer les valeur NULL (Qvariant) en Nan de panda dataframe
        df = df.where(df!=NULL)
        
        #Mettre toutes les valeurs du dataframe en réel
        df = df.astype(float)# !!! ne va pas marcher si l'identifiant de parcelle n'est pas un chiffre 
        
        #moyenne du perimetre de chaque classe
        df_mean_perimeter_zone = df.groupby([zone_id]).mean()['perimeter']
        #total du perimetre sur lchaque classe
        df_total_perimeter_zone = df.groupby([zone_id]).sum()['perimeter']
        #proportion en aire de chaque classe
        df_total_area_zone = df.groupby([zone_id]).sum()['area']
        total_area = df_total_area_zone.sum()
        df_area_ratio = (df_total_area_zone/total_area)*100
       
        #densité de chaque classe
        df_count = df.groupby(['DN']).count()['perimeter']
        nb_total = df_count.sum()
        df_class_density = df_count/nb_total
               
        #conversion des dataframes en listes
        mean_perimeter_zone = df_mean_perimeter_zone.tolist()
        area_ratio = df_area_ratio.tolist()
        total_perimeter_zone = df_total_perimeter_zone.tolist()
        class_density = df_class_density.tolist()
        
        #crééer une liste avec les indentifiants de chaque zone
        zones = df[zone_id].unique().tolist()
        nb_zones = len(zones)
        
        
        #création du fichier csv qui va contenir les données de RV
        with open(csv, 'w') as output_file:
          # write header
          line = ','.join('mean_perimeter_zone_' + str(zone) for zone in zones) + ',' + ','.join('total_perimeter_zone_' + str(zone) for zone in zones)+ ',' + ','.join('area_ratio_zone_' + str(zone) for zone in zones) + ',' + ','.join('class_density_zone_' + str(zone) for zone in zones) +  '\n'
          output_file.write(line)
          line =  ','.join(str(mean) for mean in mean_perimeter_zone) + ',' + ','.join(str(perimeter) for perimeter in total_perimeter_zone ) +',' + ','.join(str(a_ratio) for a_ratio in area_ratio) +',' + ','.join(str(density) for density in class_density) +'\n'
          output_file.write(line)
         
       
        return{self.OUTPUT : csv} 

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Donnees ecologie paysage'

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
        return self.tr('Action sur Vecteurs')

    def shortHelpString(self):
        short_help = self.tr(
            ''
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
        return 'action_sur_vecteur'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return DonneesPaysage()
