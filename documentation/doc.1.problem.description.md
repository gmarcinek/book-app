## SECNER Processing Pipeline: 1M Token Document

### Preprocessing Phase
**Input:** Dokument 1M tokenów (całe książki, długie raporty)  
**Podział na batche:** Dzielimy na fragmenty 50K-100K tokenów z nakładaniem - bo local embeddings nie udźwigną całego dokumentu naraz, a overlap zapewnia że encje na granicach nie zostaną pominięte  
**Powód strategii:** Mniejsze kawałki = szybsze przetwarzanie, nakładanie = żadna encja nie przepadnie między batches

### SECNER Chunking Per Batch
**Podział na zdania:** Każdy batch rozcinamy na pojedyncze zdania - bo zdanie to naturalna jednostka semantyczna  
**Sliding windows:** Grupujemy 3-5 zdań z 50% nakładaniem - bo pojedyncze zdanie to za mało kontekstu dla embedding, a okno daje semantic continuity  
**Tworzenie embeddingów:** Każde okno staje się wektorem liczb przez local model - bo podobne tematy mają podobne wektory  
**Analiza podobieństwa:** Porównujemy sąsiednie okna - bo spadek podobieństwa oznacza zmianę tematu/kontekstu  
**Wykrywanie granic:** Spadki poniżej progu to miejsca cięcia - bo tam następują naturalne przejścia semantyczne  
**Tworzenie chunków:** Tekst dzielony w wykrytych miejscach - bo każdy chunk będzie semantycznie spójny dla lepszego NER

### Wielorundowy NER Loop

**Runda 1: Zimny start**
- SECNER chunki trafiają do domenowej ekstrakcji encji - bo każda domena (literacka, techniczna) ma inne wzorce
- Wyciągnięte encje zapisywane z embeddingami do FAISS - bo potrzebujemy szybkiego wyszukiwania podobnych
- Graf wiedzy rozpoczyna się od pierwszego zestawu encji - bo musi mieć jakąś bazę do porównań

**Runda 2+: Ciepłe przetwarzanie**  
- Nowe chunki najpierw sprawdzane względem grafu - bo może zawierają znane już encje lub powiązane tematy
- Znalezione powiązania trafiają do promptu NER - bo context z grafu pomaga w lepszej ekstrakcji
- Ekstrakcja z wiedzą o tym co już wiemy - bo "John" w kontekście Microsoft to prawdopodobnie znana osoba
- Similarity matching przeciwko istniejącym encjom - bo "MSFT" to prawdopodobnie "Microsoft"
- Scalanie podobnych lub tworzenie nowych - bo chcemy unikać duplikatów ale także odkrywać nowe rzeczy
- Aktualizacja indeksu wektorowego - bo graf musi się uczyć z każdej rundy

### Ewolucja Grafu

**Cykl życia encji:**
- Nowa encja → embedding z kontekstem → dodanie do FAISS - bo każda encja potrzebuje swojego "odcisku palca"
- Podobna encja znaleziona → łączenie aliasów, wzbogacanie opisu - bo "Jan Kowalski" i "J. Kowalski" to ta sama osoba
- Wzrost pewności → wielokrotne wystąpienia zwiększają wiarygodność - bo częste pojawianie się potwierdza istotność

**Wnioskowanie relacji:**
- Encje w podobnych kontekstach → automatyczne linkowanie - bo co występuje razem prawdopodobnie jest powiązane
- Bliskość semantyczna → sugerowane związki - bo embedding proximity wskazuje na conceptual connections
- Wzorce współwystępowania → ocena siły połączenia - bo częste razem = silniejszy związek

**Akumulacja pamięci:**
- Gęstość grafu rośnie z każdym dokumentem - bo więcej encji = więcej potencjalnych połączeń
- Bogactwo kontekstu przez łączenie opisów - bo każdy dokument dodaje szczegóły o znanej encji  
- Jakość wyszukiwania poprawia się przez rozszerzone sieci aliasów - bo więcej sposobów odnalezienia tej samej rzeczy

### Pętla Uczenia Się Systemu

**Przetwarzanie dokumentu N czerpie korzyści z dokumentów 1...N-1:**
- Kontekst z grafu informuje o lepszej ekstrakcji - bo system już wie czego szukać
- Ustalone encje podpowiadają klasyfikację - bo "ten tekst o AI prawdopodobnie wspomni Google/OpenAI"
- Wzorce relacji kierują odkrywaniem nowych połączeń - bo jeśli CEO często łączony z firmą, nowy CEO też zostanie
- Skumulowane aliasy poprawiają rozpoznawanie - bo "MSFT" już wcześniej połączono z "Microsoft"

**Skalowanie wydajności:**
- Wyszukiwanie wektorowe pozostaje błyskawiczne - bo FAISS jest zoptymalizowany do milionów wektorów
- Przechowywanie grafu rośnie liniowo - bo każda encja to stała ilość danych
- Szybkość przetwarzania stabilizuje się - bo graf dojrzewa i mniej nowych encji trzeba dodawać  
- Jakość poprawia się asymptotycznie - bo accumulated learning ma malejące zwroty ale ciągle się poprawia

Graf staje się coraz mądrzejszy jak dziecko które uczy się języka - im więcej słyszy, tym lepiej rozumie i łączy fakty, aż w końcu potrafi przewidzieć co prawdopodobnie usłyszy w nowym kontekście.