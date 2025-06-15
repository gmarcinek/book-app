#Roadmap Book NER DDMPANER

###Recognition domain tekstu
Po rozpoznaniu czy mamy do czynienia z prozą, tekstem formalny, poezją, dziennikarstwem, dokumentacją, poradnikiem, bajką, itd. Trzeba zastosoawać dla każdego z nich strategie lub modyfikator długości chunka

###Optymalizacja wielkosci chunka per model per tresc
-Każdy model LLM ma inne max_tokens IN i OUT
-Trzeba też wziąć pod uwagę to, że nawet jeśli ma wielkie okno IN to wcale nie oznacza że trzeba je zapchać. Kierował bym się raczej wielkością OUT niż wejscia bo chodzi o ekstrakcję NER
-Wydaje mi się że żeby wyznaczyć wielkosć chunka dobrze, trzeba znać gradient gęstości informacji liczony iteracyjnie po całości dla małych chunkó po 80 tokenów z overlap 40 tokenów. Powstanje wówczas wykres średniej kroczącej dla gęstości który można użyć dla chunkowania.

###Wykrywanie sub-chunków
-etapem dodatkowym może być osobne chunkowanie encji takich jak Tabela, Wiersz, Cytat
