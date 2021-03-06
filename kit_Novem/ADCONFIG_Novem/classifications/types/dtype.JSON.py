class JSON(DataClassification):
    name = "JSON"
    usage = """
        Applies to all JSON structures if they are stored with "<fname>.json" naming convention,
        OR if they have a .json member
        """
    parent = None
    requirement = FILENAME(".*?.json") | HASMEMBER("json")
    

class H5(DataClassification):
    name  = "H5"
    usage = """
            Applies to objects that are Pandas H5 tables.
            """
    requirement = FILENAME(".*?\.h5")
    
class SETREF(DataClassification):
    name = "SETREF"
    usage  = """
                refers to other data via a *.setref
             """
    requirement = PROPERTY("_data.setref", True) | FILENAME(".*?\.setref") 

class TXT(DataClassification):
    name = "TXT"
    usage = """
            Applies to filename recognition *.txt.
            """
    parent = "SETREF"
    
    requirement = OR( FILENAME(".*?\.txt"),
                      FILENAME(".*?\.csv")
                    )
                   
class TABLE(DataClassification):
    name = "TABLE"
    usage = """
            Applies to objects that have a .json[table] member
            """
    parent = "SETREF"
    requirement =  (MEMBERCONTAINS("get('types')","TABLE") | MEMBERCONTAINS("assumed_type", "TABLE"))
                   
class METROBUSINESS(DataClassification):
    name = "METROBUSINESS"
    parent = "TABLE"
    usage = """ Applies to tables from the US Census Beaureau on Business Patterns by Metro Area, US """    
    requirement = HASMEMBER("dataframe") & MEMBERCONTAINS("dataframe.columns", "n1_4")              
