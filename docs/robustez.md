# Pruebas de robustez: por qué cada una

Una estimación sola no alcanza: cada prueba de esta lista responde a **una duda
concreta** que un lector crítico podría tener sobre el resultado. Para cada una
se explica la duda, qué se hizo y qué salió.

Todas se refieren a la **ecuación (6)**, estimada solo con Paraguay como
exportador (2012–2022, con las 3 correcciones del código activadas):

$$
Y_{ipt} = \alpha + \beta_1\, IP_{ipt} + \beta_2\, IP\_RTA\_SUBS_{ipt} + \mu_i + \lambda_t + \sigma_s + \varepsilon_{ipt}
$$

- *i* = país importador, *p* = producto (HS 6 dígitos), *t* = año, *s* = sector CIIU de 2 dígitos.
- `IP` = 1 si el importador aplica una política industrial que alcanza al producto ese año.
- `IP_RTA_SUBS` = `IP` × cobertura de disciplinas sobre subsidios del acuerdo entre Paraguay y el importador (0 a 1; Mercosur = 4/12 = 1/3).
- β₁ = efecto de una medida de un socio **sin** disciplinas sobre subsidios.
- β₁ + β₂/3 = efecto de una medida de un socio **del Mercosur**.
- Errores agrupados (*cluster*) por importador.

Las cifras completas están en [`resultados/`](../resultados) y el resumen, en el [README](../README.md#resultados).

---

## A. Antes del modelo final: diagnóstico de las regresiones simples (ecuaciones 2 a 4)

Las ecuaciones (2) a (4) son MCO sin efectos fijos. Sirven de punto de partida y
para mostrar **por qué** hace falta el modelo completo.

| Prueba | La duda | Qué salió |
|---|---|---|
| **R² y R² ajustado** | ¿Cuánto explica una sola variable? | ≤ 0,017: casi nada. Esperable: el comercio depende de muchas cosas (Wooldridge, 2010). No invalida el coeficiente, pero muestra que faltan controles. |
| **Breusch-Pagan (versión de Koenker) y White** | ¿La varianza del error es constante? Si no, los errores estándar comunes están mal. | Se rechaza (p < 0,001) → hay que usar errores robustos o agrupados. Con IP binaria, White y BP dan lo mismo. |
| **Jarque-Bera** | ¿Los errores son normales? | Se rechaza. Con 6.577 observaciones no es grave (la inferencia es asintótica), pero confirma colas muy pesadas en los montos → conviene usar logaritmos o tasas. |
| **Durbin-Watson** | ¿Los errores de un año se parecen a los del siguiente? | 0,29–0,56 (lejos de 2): autocorrelación → errores agrupados. |
| **VIF** | ¿IP e IP_RTA_SUBS están tan correlacionadas que no se pueden separar? | VIF = 1,33: no hay problema. |

## B. Diagnóstico del panel (ecuación 6)

| Prueba | La duda | Qué salió |
|---|---|---|
| **F de efectos fijos** | ¿Hacen falta los efectos fijos de importador o alcanza con una constante? | Logaritmo: F = 5,23 (p < 0,001) → **sí** hacen falta. Crecimiento: F = 0,75 (p = 0,97) → no tanto: la tasa de crecimiento ya elimina las diferencias de nivel entre destinos. |
| **Hausman–Mundlak** | ¿Efectos fijos o aleatorios? Los aleatorios suponen que lo propio de cada destino no está correlacionado con las medidas. | Logaritmo: 58,4 (p < 0,001) → **efectos fijos**. Crecimiento: 1,55 (p = 0,46) → ambos darían lo mismo. |
| **Wooldridge (autocorrelación en panel)** | ¿Hay persistencia en los errores de un mismo flujo? | Logaritmo: ρ = −0,22, se rechaza la ausencia de autocorrelación → errores agrupados por importador. Crecimiento: ρ = −0,52, no se rechaza. |

## C. ¿El resultado depende de cómo se mide la variable dependiente?

| Prueba | La duda | Qué salió |
|---|---|---|
| **Logaritmo vs. tasa de crecimiento** | El protocolo de la tesis fijó el logaritmo de las exportaciones; el paper usa la tasa de crecimiento. ¿Coinciden? | Coinciden en que la profundidad del acuerdo (β₂) protege. En crecimiento, además, β₁ = **−6,77 pp** (p = 0,038): sin disciplinas, la medida frena las exportaciones. |
| **Sin valores atípicos** (\|crecimiento\| < 200 %) | Una tasa de crecimiento explota cuando la base es chica (de USD 1 a USD 10 = +900 %). ¿Unos pocos casos extremos arrastran el resultado? | Mismo criterio que la Tabla 5 del paper. El resultado se mantiene (crecimiento: β₁ = −6,37; β₂ = 36,1, p < 0,001). |
| **Umbral de USD 1 millón** | El paper solo usa flujos mayores a USD 1 millón (nota 3); los flujos chicos son más ruidosos. ¿Cambia algo? | β₂ se mantiene; β₁ pierde precisión (−4,80; p = 0,13) porque se pierde entre un quinto y un tercio de la muestra. |
| **Por sector** (agro, alimentos, manufacturas) | ¿El efecto es parejo o se concentra en algún tipo de producto? | En crecimiento: en **alimentos** β₁ = −12,1 pp (p = 0,013) y el Mercosur no compensa (−7,6 pp); en **manufacturas** el acuerdo protege mucho (β₂ = 67,9; Mercosur +21,7 pp). |
| **PPML (Poisson)** | Con comercio, el logaritmo puede sesgar los coeficientes cuando la varianza cambia con el tamaño del flujo (Santos Silva y Tenreyro, 2006). Es el estimador estándar de los modelos de gravedad (Yotov et al., 2016). | β₂ = 1,93 (p = 0,022): misma dirección. |

## D. ¿Es un efecto causal o una coincidencia?

Ésta es la duda más importante. Los gobiernos no eligen al azar a qué sectores
ayudar: quizás apoyan justo a los sectores donde Paraguay ya venía creciendo (o
cayendo). Si es así, la regresión mostraría una "relación" que no es efecto de la medida.

| Prueba | La duda | Qué salió |
|---|---|---|
| **Placebo: medida del año siguiente (t+1)** | Una medida que todavía no existe **no puede** afectar las exportaciones de hoy. Si el coeficiente del adelanto sale significativo, algo distinto de la medida está detrás (prueba de exogeneidad estricta; Wooldridge, 2010, §10.7.1). | Crecimiento: −4,71 (p = 0,73) → **pasa**. Logaritmo: 0,54 (p = 0,040) → **falla**: en niveles, los productos alcanzados ya eran distintos antes de la medida. |
| **Rezagos (t−1 y t−2)** | ¿El efecto aparece de golpe, tarda, o se desplaza en el tiempo? | Crecimiento: rezagos no significativos → el efecto ocurre el mismo año, sin arrastre. Logaritmo: rezagos positivos y significativos (otra señal de composición, no de efecto). |
| **Efectos fijos de producto** | Comparar **el mismo producto** antes y después de la medida, en lugar de productos distintos entre sí. | Crecimiento: β₂ sube a 64,3 (p < 0,001). Logaritmo: cae a 0,19 (p = 0,41) y **desaparece**. |
| **Efectos fijos de importador × producto** | Lo mismo, pero para cada destino-producto: es lo que hace el paper. | Crecimiento: 55,9 (p < 0,001). Logaritmo: 0,06 (p = 0,70). |

**Conclusión de este bloque:** en tasa de crecimiento el resultado resiste las
cuatro pruebas; en logaritmo, no. El efecto en niveles refleja sobre todo **qué
productos** se exportan a cada socio (selección), no el efecto de las medidas.
Por eso la tasa de crecimiento (la especificación del paper) es la más creíble,
aunque el protocolo de la tesis fijara el logaritmo como principal.

## E. ¿Los p-valores son confiables con tan pocos socios tratados?

`IP_RTA_SUBS` solo es distinto de cero para **tres** socios (Brasil, Argentina
y Uruguay, por el Mercosur), y Brasil pesa entre el 50 % y el 80 %. Los errores
agrupados por importador suponen muchos grupos que aportan información; aquí, en
la práctica, son entre 1,5 y 7 "grupos efectivos" de unos 100. En esa situación
los errores estándar habituales suelen ser **demasiado chicos** (Cameron, Gelbach
y Miller, 2008; MacKinnon y Webb, 2017).

| Prueba | La duda | Qué salió (β₂, crecimiento / logaritmo) |
|---|---|---|
| **Bootstrap salvaje por grupos** (*wild cluster bootstrap*, 9.999 repeticiones) | Recalcula el p-valor sin depender de que haya muchos grupos. | p = 0,032 / 0,071 |
| **Sorteo de socios placebo** (inferencia por aleatorización, 1.999 sorteos) | Si se asignara la cobertura del Mercosur a tres socios **al azar**, ¿qué tan seguido saldría un coeficiente tan grande como el real? | p = 0,046 / 0,048: el resultado real es raro bajo el azar. |
| **Errores agrupados por importador y año** | Hay shocks que afectan a todos los destinos el mismo año (por ejemplo, la pandemia de 2020; Cameron, Gelbach y Miller, 2011). | p = 0,052 / 0,019 |
| **Sin Brasil** | Si un solo socio domina, ¿el resultado es "del Mercosur" o "de Brasil"? | 29,4 (p = 0,012) / 1,08 (p < 0,001): sigue sin Brasil, aunque más chico en crecimiento. |
| **Bootstrap del efecto neto del Mercosur** (β₁ + β₂/3) | El efecto neto positivo para un socio del Mercosur, ¿es robusto? | p = 0,61 / 0,17: **no**. Se puede afirmar que el Mercosur protege (el efecto neto no es negativo), no que aumente las exportaciones. |

## F. Complementos

| Prueba | La duda | Qué salió |
|---|---|---|
| **Subperíodos 2012–2019 vs. 2020–2022** | Las medidas se disparan desde 2020 (pandemia). ¿El resultado es solo de esos años? | El efecto ya está en 2012–2019; en 2020–2022 hay pocas observaciones tratadas y es impreciso. No hay quiebre significativo. |
| **Un solo tipo de subsidio** (incentivos fiscales a la exportación) | ¿Algún instrumento explica todo? | Domina un programa brasileño de reintegros a la exportación, pero el resultado no es robusto (bootstrap p = 0,13–0,21; sin Brasil desaparece). Se usa solo como ilustración. |
| **Simulación GTAP** (equilibrio general) | La regresión mira hacia atrás; ¿qué predice un modelo de toda la economía mundial? | Un subsidio del 10 % de Brasil a 4 sectores reduce un 4,25 % lo que Paraguay le vende en esos sectores; si se recorta en un tercio (como haría una disciplina), la caída es de 3,19 %. |

---

## Referencias

- Barattieri, A., Mattoo, A. y Taglioni, D. (2024). *Trade Effects of Industrial Policies: Are Preferential Agreements a Shield?* Policy Research Working Paper 10806, Banco Mundial.
- Cameron, A. C., Gelbach, J. B. y Miller, D. L. (2008). Bootstrap-based improvements for inference with clustered errors. *Review of Economics and Statistics*, 90(3), 414–427.
- Cameron, A. C., Gelbach, J. B. y Miller, D. L. (2011). Robust inference with multiway clustering. *Journal of Business & Economic Statistics*, 29(2), 238–249.
- MacKinnon, J. G. y Webb, M. D. (2017). Wild bootstrap inference for wildly different cluster sizes. *Journal of Applied Econometrics*, 32(2), 233–254.
- Santos Silva, J. M. C. y Tenreyro, S. (2006). The log of gravity. *Review of Economics and Statistics*, 88(4), 641–658.
- Wooldridge, J. M. (2010). *Econometric Analysis of Cross Section and Panel Data* (2.ª ed.). MIT Press.
- Yotov, Y. V., Piermartini, R., Monteiro, J.-A. y Larch, M. (2016). *An Advanced Guide to Trade Policy Analysis: The Structural Gravity Model*. OMC y UNCTAD.
