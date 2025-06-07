"""
NER Validation - Walidacja relacji i filtrowanie nonsensownych powiązań
Zapobiega powstawaniu błędnych relacji w grafie wiedzy
"""

from typing import Dict, List, Any, Set, Tuple
from .consts import RELATIONSHIP_TYPES, ENTITY_TYPES_FLAT

class RelationshipValidator:
    """
    Walidator relacji zapobiegający nonsensownym powiązaniom
    """
    
    def __init__(self):
        # Dozwolone kombinacje typu relacji -> (source_type, target_type)
        self.valid_combinations = self._build_valid_combinations()
        
        # Blacklista nonsensownych relacji
        self.blacklisted_patterns = self._build_blacklist()
        
        # Wymagane pola dla różnych typów relacji
        self.required_fields = {
            'internal': ['type', 'target_entity', 'evidence', 'confidence'],
            'external': ['type', 'value', 'source'],
            'pending': ['name', 'type', 'reason']
        }
    
    def _build_valid_combinations(self) -> Dict[str, Set[Tuple[str, str]]]:
        """
        Zdefiniuj logiczne kombinacje relacji między typami encji
        """
        valid_combos = {}
        
        # Relacje strukturalne
        valid_combos['uses'] = {
            ('OSOBA', 'PRZEDMIOT'), ('OSOBA', 'USŁUGA'),
            ('PRZEDMIOT', 'USŁUGA'), ('ORGANIZACJA', 'PRZEDMIOT'),
            ('ORGANIZACJA', 'USŁUGA')
        }
        
        valid_combos['requires'] = {
            ('PRZEDMIOT', 'USŁUGA'), ('PRZEDMIOT', 'PRZEDMIOT'),
            ('USŁUGA', 'USŁUGA'), ('OSOBA', 'USŁUGA')
        }
        
        valid_combos['contains'] = {
            ('MIEJSCE', 'PRZEDMIOT'), ('MIEJSCE', 'OSOBA'),
            ('ORGANIZACJA', 'OSOBA'), ('PRZEDMIOT', 'PRZEDMIOT')
        }
        
        valid_combos['located_in'] = {
            ('OSOBA', 'MIEJSCE'), ('PRZEDMIOT', 'MIEJSCE'),
            ('ORGANIZACJA', 'MIEJSCE'), ('USŁUGA', 'MIEJSCE')
        }
        
        valid_combos['owns'] = {
            ('OSOBA', 'PRZEDMIOT'), ('OSOBA', 'MIEJSCE'),
            ('ORGANIZACJA', 'PRZEDMIOT'), ('ORGANIZACJA', 'MIEJSCE')
        }
        
        valid_combos['creates'] = {
            ('OSOBA', 'PRZEDMIOT'), ('OSOBA', 'KONCEPCJA'),
            ('ORGANIZACJA', 'PRZEDMIOT'), ('ORGANIZACJA', 'USŁUGA')
        }
        
        valid_combos['part_of'] = {
            ('PRZEDMIOT', 'PRZEDMIOT'), ('OSOBA', 'ORGANIZACJA'),
            ('MIEJSCE', 'MIEJSCE'), ('USŁUGA', 'USŁUGA')
        }
        
        # Relacje semantyczne - bardziej uniwersalne
        semantic_types = [
            'related_to', 'similar_to', 'opposite_of',
            'cause_of', 'effect_of', 'enables'
        ]
        
        all_entity_pairs = {
            (source, target) 
            for source in ENTITY_TYPES_FLAT 
            for target in ENTITY_TYPES_FLAT 
            if source != target
        }
        
        for rel_type in semantic_types:
            valid_combos[rel_type] = all_entity_pairs
        
        return valid_combos
    
    def _build_blacklist(self) -> List[Dict[str, str]]:
        """
        Zdefiniuj patterns nonsensownych relacji do odrzucenia
        """
        return [
            # Relacje encji z samą sobą
            {'pattern': 'self_reference', 'description': 'Encja ma relację ze sobą'},
            
            # Nonsensowne relacje "uses"
            {'pattern': 'place_uses_place', 'relation': 'uses', 'source_type': 'MIEJSCE', 'target_type': 'MIEJSCE'},
            {'pattern': 'concept_uses_object', 'relation': 'uses', 'source_type': 'KONCEPCJA', 'target_type': 'PRZEDMIOT'},
            
            # Nonsensowne relacje "contains"
            {'pattern': 'object_contains_place', 'relation': 'contains', 'source_type': 'PRZEDMIOT', 'target_type': 'MIEJSCE'},
            {'pattern': 'service_contains_object', 'relation': 'contains', 'source_type': 'USŁUGA', 'target_type': 'PRZEDMIOT'},
            
            # Nonsensowne relacje "requires"
            {'pattern': 'place_requires_person', 'relation': 'requires', 'source_type': 'MIEJSCE', 'target_type': 'OSOBA'},
        ]
    
    def validate_internal_relationship(self, relationship: Dict[str, Any], 
                                     source_entity: Dict[str, Any],
                                     available_entities: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Waliduj relację wewnętrzną (między encjami w grafie)
        
        Returns:
            (is_valid, reason)
        """
        # Sprawdź wymagane pola
        if not self._check_required_fields(relationship, 'internal'):
            return False, "Brakujące wymagane pola"
        
        rel_type = relationship.get('type', '').strip()
        target_name = relationship.get('target_entity', '').strip()
        source_name = source_entity.get('name', '').strip()
        
        # Sprawdź czy relacja ze sobą
        if source_name.lower() == target_name.lower():
            return False, f"Relacja ze sobą: {source_name}"
        
        # Sprawdź czy typ relacji jest dozwolony
        if not self._is_valid_relationship_type(rel_type):
            return False, f"Niedozwolony typ relacji: {rel_type}"
        
        # Znajdź encję docelową
        target_entity = None
        for entity in available_entities:
            if entity.get('name', '').strip().lower() == target_name.lower():
                target_entity = entity
                break
        
        if not target_entity:
            return False, f"Nie znaleziono encji docelowej: {target_name}"
        
        # Sprawdź kombinację typów
        source_type = source_entity.get('type', '')
        target_type = target_entity.get('type', '')
        
        if not self._is_valid_type_combination(rel_type, source_type, target_type):
            return False, f"Niedozwolona kombinacja: {source_type} --{rel_type}--> {target_type}"
        
        # Sprawdź blacklistę
        if self._is_blacklisted(rel_type, source_type, target_type, source_name, target_name):
            return False, f"Relacja na blackliście: {source_name} --{rel_type}--> {target_name}"
        
        # Sprawdź confidence
        confidence = relationship.get('confidence', 0)
        if not isinstance(confidence, (int, float)) or confidence < 0.3:
            return False, f"Zbyt niska pewność: {confidence}"
        
        return True, "OK"
    
    def validate_external_relationship(self, relationship: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Waliduj relację zewnętrzną (z wartościami spoza grafu)
        """
        if not self._check_required_fields(relationship, 'external'):
            return False, "Brakujące wymagane pola"
        
        rel_type = relationship.get('type', '').strip()
        value = relationship.get('value', '').strip()
        
        if not self._is_valid_relationship_type(rel_type):
            return False, f"Niedozwolony typ relacji: {rel_type}"
        
        if len(value) < 2:
            return False, "Zbyt krótka wartość relacji"
        
        # Sprawdź czy wartość nie jest listą wszystkich encji (częsty błąd LLM)
        if ',' in value and len(value.split(',')) > 5:
            return False, "Wartość wygląda jak lista wszystkich encji"
        
        return True, "OK"
    
    def validate_pending_entity(self, pending: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Waliduj brakującą encję
        """
        if not self._check_required_fields(pending, 'pending'):
            return False, "Brakujące wymagane pola"
        
        name = pending.get('name', '').strip()
        entity_type = pending.get('type', '').strip()
        reason = pending.get('reason', '').strip()
        
        if len(name) < 2:
            return False, "Zbyt krótka nazwa encji"
        
        if entity_type not in ENTITY_TYPES_FLAT:
            return False, f"Niedozwolony typ encji: {entity_type}"
        
        if len(reason) < 5:
            return False, "Zbyt krótki powód"
        
        return True, "OK"
    
    def _check_required_fields(self, item: Dict[str, Any], item_type: str) -> bool:
        """Sprawdź czy wszystkie wymagane pola są obecne"""
        required = self.required_fields.get(item_type, [])
        return all(
            field in item and 
            item[field] is not None and 
            str(item[field]).strip() 
            for field in required
        )
    
    def _is_valid_relationship_type(self, rel_type: str) -> bool:
        """Sprawdź czy typ relacji jest na liście dozwolonych"""
        all_types = []
        for category_types in RELATIONSHIP_TYPES.values():
            all_types.extend(category_types)
        return rel_type in all_types
    
    def _is_valid_type_combination(self, rel_type: str, source_type: str, target_type: str) -> bool:
        """Sprawdź czy kombinacja typów jest dozwolona dla danej relacji"""
        if rel_type not in self.valid_combinations:
            return True  # Jeśli nie ma ograniczeń, pozwól
        
        valid_pairs = self.valid_combinations[rel_type]
        return (source_type, target_type) in valid_pairs
    
    def _is_blacklisted(self, rel_type: str, source_type: str, target_type: str, 
                       source_name: str, target_name: str) -> bool:
        """Sprawdź czy relacja jest na blackliście"""
        for pattern in self.blacklisted_patterns:
            if pattern.get('relation') == rel_type:
                if (pattern.get('source_type') == source_type and 
                    pattern.get('target_type') == target_type):
                    return True
        return False
    
    def filter_relationships(self, entity_data: Dict[str, Any], 
                           available_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Filtruj wszystkie relacje encji i pozostaw tylko poprawne
        
        Args:
            entity_data: Dane encji z relacjami
            available_entities: Lista wszystkich dostępnych encji
            
        Returns:
            Przefiltrowane dane encji
        """
        filtered_data = entity_data.copy()
        relationships = entity_data.get('relationships', {})
        
        # Filtruj relacje wewnętrzne
        internal_rels = relationships.get('internal', [])
        valid_internal = []
        
        for rel in internal_rels:
            is_valid, reason = self.validate_internal_relationship(rel, entity_data, available_entities)
            if is_valid:
                valid_internal.append(rel)
            else:
                print(f"Odrzucono relację wewnętrzną: {reason}")
        
        # Filtruj relacje zewnętrzne
        external_rels = relationships.get('external', [])
        valid_external = []
        
        for rel in external_rels:
            is_valid, reason = self.validate_external_relationship(rel)
            if is_valid:
                valid_external.append(rel)
            else:
                print(f"Odrzucono relację zewnętrzną: {reason}")
        
        # Filtruj brakujące encje
        pending_ents = relationships.get('pending', [])
        valid_pending = []
        
        for pending in pending_ents:
            is_valid, reason = self.validate_pending_entity(pending)
            if is_valid:
                valid_pending.append(pending)
            else:
                print(f"Odrzucono brakującą encję: {reason}")
        
        # Aktualizuj przefiltrowane relacje
        filtered_data['relationships'] = {
            'internal': valid_internal,
            'external': valid_external,
            'pending': valid_pending
        }
        
        return filtered_data
    
    def get_validation_stats(self, results: List[Tuple[bool, str]]) -> Dict[str, Any]:
        """Generuj statystyki walidacji"""
        valid_count = sum(1 for is_valid, _ in results if is_valid)
        total_count = len(results)
        
        # Policz przyczyny odrzuceń
        rejection_reasons = {}
        for is_valid, reason in results:
            if not is_valid:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        return {
            'total_validated': total_count,
            'valid_relationships': valid_count,
            'rejected_relationships': total_count - valid_count,
            'validation_rate': valid_count / total_count if total_count > 0 else 0,
            'rejection_reasons': rejection_reasons
        }