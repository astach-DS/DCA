import pyodbc
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import numpy as np

# Set dafault parameters
plt.rcParams['axes.titlesize'] = 20
plt.rcParams["figure.titlesize"] = 19
plt.rcParams['axes.labelsize'] = 16
plt.rcParams["figure.figsize"] = (10,7)
plt.rcParams["xtick.labelsize"] = 14
plt.rcParams["ytick.labelsize"] = 14

def hyperbolic_equation(t, qi, b, di):
    """
    Hyperbolic decline curve equation
    Arguments:
        t: Float. Time since the well first came online, can be in various units 
        (days, months, etc) so long as they are consistent.
        qi: Float. Initial production rate when well first came online.
        b: Float. Hyperbolic decline constant
        di: Float. Nominal decline rate at time t=0
    Output: 
        Returns q, or the expected production rate at time t. Float.
    """
    return qi/((1.0+b*di*t)**(1.0/b))

def get_max_initial_production(months):
    ''' id_pozo(int) = The well you want to get the max initial production
        months(int) = How many month since start production you want to search the max'''
    
    max_initial_production = produccion_pozo.head(months).sort_values(ascending=False)[0]
    return max_initial_production

# Set driver for MS Access and file path
driver = '{Microsoft Access Driver (*.mdb, *.accdb)}'
filepath = r'C:\Users\Juli\Documents\DH\contenido\ds_blend_students_2020\Wells Decline\Produccion NOC SEN_Valida.accdb'

# Stablish conection and set cursor
conn = pyodbc.connect(driver=driver,dbq=filepath)
cursor = conn.cursor()

# Query
query = 'SELECT IDPOZO,FECHA,QO_EF FROM POZOS_FORM_PRODUCCION ORDER BY IDPOZO,FECHA'

# Convert the query into df and make change name of columns to lowercase
df = pd.read_sql_query(query, conn)
df.columns = df.columns.str.lower()

# Set fecha as index
df.set_index('fecha',inplace=True)

# Set go_ef_mes and delete qo_ef
df['qo_ef_mes'] = df['qo_ef'] * 30.4167
del df['qo_ef']

for id_pozo in ids_pozos:
    # Production rate Series of the well id_pozo
    produccion_pozo = df[df['idpozo']==id_pozo]['qo_ef_mes']


    # Set the max initial production rate as qi
    qi = get_max_initial_production(6)
    # Search the index where qo = qi(max)
    for index_mes_inicial,qo in enumerate(produccion_pozo):
        if qo == qi:
            break

    # Production rates since qi
    caudales = produccion_pozo[index_mes_inicial:].values
    # Number of months the well produced since qi
    numero_meses = np.arange(len(produccion_pozo.index) - index_mes_inicial)

    #Hyperbolic curve fit the data to get best fit equation
    popt_hyp, pcov_hyp=curve_fit(hyperbolic_equation, numero_meses,caudales,bounds=(0, [qi,2,20]))
    print('Hyperbolic Fit Curve-fitted Variables: qi='+str(popt_hyp[0])+', b='+str(popt_hyp[1])+', di='+str(popt_hyp[2]))

    # Create a list of number of month to forecast
    meses_pronostico = list(np.arange(len(produccion_pozo.index)))
    for i in np.arange(meses_pronostico[-1]+1,meses_pronostico[-1]+13,1):
        meses_pronostico.append(i)
    
    # Production rate forecast
    qo_prono = [hyperbolic_equation(mes,qi,popt_hyp[1],popt_hyp[2]) for mes in meses_pronostico]

    # Slices meses_pronostico so it starts from when qi = max production rate happened
    meses_pronostico = meses_pronostico[index_mes_inicial:]

    # Slices qo_prono so it matchs meses_pronostico lenght
    qo_prono = qo_prono[:-index_mes_inicial]

    # Plot the Forecast
    x=np.arange(len(produccion_pozo.index))
    y=produccion_pozo.values
    plt.plot(x,y,label=f'real id_pozo = {id_pozo}')
    plt.plot(meses_pronostico,qo_prono,linestyle='--',label='Pronóstico')
    plt.xlabel('Numero de Meses')
    plt.ylabel('Caudal Petróleo m^3')
    plt.title(f'Pronóstico para el pozo = {id_pozo}')
    plt.legend()
    plt.show()

    # Writting forecast into data base
    meses_pronostico = list(map(int,meses_pronostico))
    qo_prono = list(map(float,qo_prono))
    id_pozo = list(map(int,[id_pozo]*len(qo_prono)))
    Pronos_DCA = list(zip(id_pozo,meses_pronostico,qo_prono))
    
    # Creating the table in the DB
    try:
        cursor.execute('create table prono_andres (id_pozo int, numero_meses int,qo_pronostico float)')
        cursor.commit()
    except:
        print('La tabla ya existe')
        
    # Insert the data into de table
    query = f'SELECT id_pozo FROM prono_andres WHERE id_pozo = {id_pozo[0]}'
    cursor.execute(query)
    if not cursor.fetchall():
        cursor.executemany("""insert into prono_andres (id_pozo , numero_meses, qo_pronostico) values(?,?,?)""", Pronos_DCA)
        cursor.commit()
        print('La información se ha insertado correctamente')
    else:
        print(f'El pozo {id_pozo[0]} ya existe en la db')
