// Generado por resultados/datos_pagina.py a partir de resultados/*.csv
const DATOS = {
 "medidas": {
  "anios": [
   2012,
   2013,
   2014,
   2015,
   2016,
   2017,
   2018,
   2019,
   2020,
   2021,
   2022
  ],
  "paises": {
   "Argentina": [
    5,
    4,
    6,
    14,
    18,
    17,
    36,
    30,
    26,
    35,
    49
   ],
   "Brasil": [
    32,
    55,
    99,
    47,
    26,
    34,
    52,
    41,
    78,
    89,
    147
   ],
   "Chile": [
    0,
    0,
    1,
    1,
    0,
    0,
    0,
    0,
    9,
    5,
    2
   ],
   "Alemania": [
    140,
    174,
    150,
    147,
    144,
    112,
    146,
    153,
    195,
    221,
    203
   ],
   "India": [
    29,
    45,
    35,
    43,
    26,
    32,
    55,
    32,
    64,
    72,
    49
   ],
   "Israel": [
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    2,
    6,
    3
   ],
   "Italia": [
    66,
    70,
    82,
    106,
    119,
    125,
    92,
    103,
    177,
    242,
    271
   ],
   "Perú": [
    0,
    0,
    1,
    1,
    0,
    0,
    1,
    0,
    13,
    3,
    8
   ],
   "Rusia": [
    33,
    47,
    61,
    75,
    86,
    76,
    33,
    28,
    48,
    46,
    61
   ],
   "Turquía": [
    6,
    5,
    5,
    9,
    23,
    17,
    29,
    42,
    69,
    43,
    42
   ],
   "Uruguay": [
    6,
    1,
    0,
    0,
    0,
    0,
    2,
    0,
    4,
    0,
    0
   ],
   "Estados Unidos": [
    557,
    425,
    435,
    356,
    247,
    222,
    233,
    234,
    1348,
    844,
    589
   ],
   "Total": [
    875,
    826,
    875,
    799,
    689,
    635,
    679,
    663,
    2033,
    1606,
    1424
   ]
  }
 },
 "exposicion": [
  {
   "p": "Rusia",
   "v": 70.9,
   "a": 5475.1,
   "t": 7723.2,
   "prod": "soja"
  },
  {
   "p": "Brasil",
   "v": 59.8,
   "a": 19532.6,
   "t": 32665.1,
   "prod": "energía eléctrica"
  },
  {
   "p": "Alemania",
   "v": 53.4,
   "a": 954.0,
   "t": 1788.0,
   "prod": "soja"
  },
  {
   "p": "Italia",
   "v": 46.4,
   "a": 1151.6,
   "t": 2481.4,
   "prod": "harina y tortas de soja"
  },
  {
   "p": "Estados Unidos",
   "v": 43.5,
   "a": 967.9,
   "t": 2223.2,
   "prod": "azúcar"
  },
  {
   "p": "Argentina",
   "v": 33.8,
   "a": 4991.8,
   "t": 14756.9,
   "prod": "soja"
  },
  {
   "p": "India",
   "v": 2.1,
   "a": 41.1,
   "t": 1964.3,
   "prod": "aceite de soja"
  },
  {
   "p": "Uruguay",
   "v": 0.9,
   "a": 13.8,
   "t": 1547.9,
   "prod": "tabaco"
  },
  {
   "p": "Turquía",
   "v": 0.1,
   "a": 2.0,
   "t": 1422.8,
   "prod": "arroz"
  },
  {
   "p": "Perú",
   "v": 0.1,
   "a": 0.9,
   "t": 1523.3,
   "prod": "arroz"
  },
  {
   "p": "Chile",
   "v": 0.0,
   "a": 0.0,
   "t": 7313.2,
   "prod": ""
  },
  {
   "p": "Israel",
   "v": 0.0,
   "a": 0.0,
   "t": 1567.5,
   "prod": ""
  }
 ],
 "especificaciones": {
  "crec": {
   "b1": -6.76823,
   "b2": 44.2519,
   "v1": 10.3736170561,
   "v2": 111.44391488999999,
   "c": -17.340737018999995,
   "que": "el crecimiento de las exportaciones paraguayas de ese producto",
   "unidad": "puntos porcentuales",
   "dec": 2,
   "paso": 10
  },
  "log": {
   "b1": 0.132679,
   "b2": 1.06938,
   "v1": 0.004978487810559999,
   "v2": 0.056624009764,
   "c": -0.015284085897171664,
   "que": "el valor exportado de ese producto (en logaritmo)",
   "unidad": "unidades de logaritmo",
   "dec": 3,
   "paso": 0.5
  }
 },
 "robustez": [
  {
   "e": "Logaritmo",
   "t": "Errores agrupados por importador (base)",
   "corto": "Base",
   "p": 1.51221e-05,
   "duda": "Es la estimación principal: los errores se agrupan por país de destino, porque las exportaciones a un mismo país se parecen entre sí.",
   "res": "Significativo en la estimación base."
  },
  {
   "e": "Logaritmo",
   "t": "Bootstrap salvaje (9.999 repeticiones)",
   "corto": "Bootstrap salvaje",
   "p": 0.0711071,
   "duda": "Solo tres socios (los del MERCOSUR) tienen reglas sobre subsidios en los datos. Con tan pocos, los errores habituales suelen salir demasiado chicos; el bootstrap recalcula el p-valor sin depender de eso.",
   "res": "Pierde fuerza: significativo solo al 10 %."
  },
  {
   "e": "Logaritmo",
   "t": "Sorteo de socios placebo (1.999)",
   "corto": "Sorteo de socios",
   "p": 0.048,
   "duda": "Si se le asignara el acuerdo a tres socios al azar, ¿qué tan seguido saldría un resultado tan grande como el real? Si es raro, el resultado no es casualidad.",
   "res": "Raro bajo el azar."
  },
  {
   "e": "Logaritmo",
   "t": "Errores agrupados por importador y año",
   "corto": "Por importador y año",
   "p": 0.0189656,
   "duda": "Hay golpes que afectan a todos los destinos el mismo año, como la pandemia de 2020. Esta prueba los tiene en cuenta.",
   "res": "Se mantiene."
  },
  {
   "e": "Logaritmo",
   "t": "Sin Brasil",
   "corto": "Sin Brasil",
   "p": 9.42996e-07,
   "duda": "Brasil pesa entre el 50 % y el 80 % de la información. ¿El resultado es del MERCOSUR o solo de Brasil?",
   "res": "Se mantiene sin Brasil."
  },
  {
   "e": "Logaritmo",
   "t": "Efectos fijos de producto",
   "corto": "Mismo producto",
   "p": 0.406895,
   "duda": "Compara el mismo producto antes y después de la medida, en lugar de productos distintos entre sí.",
   "res": "Desaparece: en logaritmo, el resultado reflejaba qué productos se exportan a cada socio, no el efecto de las medidas."
  },
  {
   "e": "Logaritmo",
   "t": "Efectos fijos de importador por producto",
   "corto": "Mismo destino y producto",
   "p": 0.69614,
   "duda": "Lo mismo, pero para cada combinación de destino y producto: es lo que hace el estudio original.",
   "res": "Desaparece, por la misma razón."
  },
  {
   "e": "Logaritmo",
   "t": "Bootstrap del efecto neto del Mercosur",
   "corto": "Efecto neto MERCOSUR",
   "p": 0.165917,
   "duda": "Ésta no mide el escudo sino algo más: si con un socio del MERCOSUR las exportaciones llegan a subir. Se prueba con bootstrap, por los pocos socios.",
   "res": "No resiste."
  },
  {
   "e": "Tasa de crecimiento",
   "t": "Errores agrupados por importador (base)",
   "corto": "Base",
   "p": 5.86295e-05,
   "duda": "Es la estimación principal: los errores se agrupan por país de destino, porque las exportaciones a un mismo país se parecen entre sí.",
   "res": "Significativo: con más reglas sobre subsidios, la medida perjudica menos."
  },
  {
   "e": "Tasa de crecimiento",
   "t": "Bootstrap salvaje (9.999 repeticiones)",
   "corto": "Bootstrap salvaje",
   "p": 0.0318032,
   "duda": "Solo tres socios (los del MERCOSUR) tienen reglas sobre subsidios en los datos. Con tan pocos, los errores habituales suelen salir demasiado chicos; el bootstrap recalcula el p-valor sin depender de eso.",
   "res": "Sigue significativo al 5 %."
  },
  {
   "e": "Tasa de crecimiento",
   "t": "Sorteo de socios placebo (1.999)",
   "corto": "Sorteo de socios",
   "p": 0.0455,
   "duda": "Si se le asignara el acuerdo a tres socios al azar, ¿qué tan seguido saldría un resultado tan grande como el real? Si es raro, el resultado no es casualidad.",
   "res": "El resultado real es raro bajo el azar: no es casualidad."
  },
  {
   "e": "Tasa de crecimiento",
   "t": "Errores agrupados por importador y año",
   "corto": "Por importador y año",
   "p": 0.0520275,
   "duda": "Hay golpes que afectan a todos los destinos el mismo año, como la pandemia de 2020. Esta prueba los tiene en cuenta.",
   "res": "Queda justo en el límite (5 %); significativo al 10 %."
  },
  {
   "e": "Tasa de crecimiento",
   "t": "Sin Brasil",
   "corto": "Sin Brasil",
   "p": 0.0122576,
   "duda": "Brasil pesa entre el 50 % y el 80 % de la información. ¿El resultado es del MERCOSUR o solo de Brasil?",
   "res": "Se mantiene sin Brasil, aunque más chico."
  },
  {
   "e": "Tasa de crecimiento",
   "t": "Efectos fijos de producto",
   "corto": "Mismo producto",
   "p": 1.52461e-05,
   "duda": "Compara el mismo producto antes y después de la medida, en lugar de productos distintos entre sí.",
   "res": "Se hace más fuerte: no es un efecto de qué productos se exportan."
  },
  {
   "e": "Tasa de crecimiento",
   "t": "Efectos fijos de importador por producto",
   "corto": "Mismo destino y producto",
   "p": 5.80851e-05,
   "duda": "Lo mismo, pero para cada combinación de destino y producto: es lo que hace el estudio original.",
   "res": "También se mantiene, como en el estudio original."
  },
  {
   "e": "Tasa de crecimiento",
   "t": "Bootstrap del efecto neto del Mercosur",
   "corto": "Efecto neto MERCOSUR",
   "p": 0.607761,
   "duda": "Ésta no mide el escudo sino algo más: si con un socio del MERCOSUR las exportaciones llegan a subir. Se prueba con bootstrap, por los pocos socios.",
   "res": "No resiste: el MERCOSUR protege (el efecto neto no es negativo), pero no se puede afirmar que haga subir las exportaciones."
  }
 ],
 "gtap": [
  {
   "s": "Oleaginosas",
   "sub": true,
   "s1": -8.31,
   "s3": -5.98
  },
  {
   "s": "Otros alimentos",
   "sub": true,
   "s1": -4.19,
   "s3": -3.3
  },
  {
   "s": "Otras manufacturas",
   "sub": true,
   "s1": -1.88,
   "s3": -1.41
  },
  {
   "s": "Cereales",
   "sub": true,
   "s1": -1.15,
   "s3": -1.15
  },
  {
   "s": "Aceites vegetales",
   "sub": false,
   "s1": 17.59,
   "s3": 11.01
  },
  {
   "s": "Electricidad",
   "sub": false,
   "s1": 18.96,
   "s3": 12.1
  },
  {
   "s": "Manufacturas livianas",
   "sub": false,
   "s1": 24.19,
   "s3": 15.2
  },
  {
   "s": "Carne bovina",
   "sub": false,
   "s1": 36.71,
   "s3": 22.55
  }
 ]
};
