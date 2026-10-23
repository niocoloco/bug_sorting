from src.bug_sortingv1_0.vector_db import init_lancedb, find_similar_feedback

def esegui_test_videogioco():
    # 1. Inizializzazione
    db = init_lancedb()
    table = db.open_table("feedback_vectors")
    
    # 2. Inserimento record fittizi (Simula l'output testuale già unito)
    dati_fittizi = [
        {
            "ticket_id": 101,
            "platform": "UNKNOWN",
            "category": "balancement_request",
            "text": "Spada lunga +7 sbilanciata Da quando è stata introdotta la spada lunga +7, il gioco è diventato ingiocabile perché risulta troppo forte e impossibile da counterare. Segnalazione di sbilanciamento legata all'oggetto spada lunga +7."
        },
        {
            "ticket_id": 102,
            "platform": "PS5",
            "category": "bug",
            "text": "Glitch compenetrazione locanda Personaggio cade sotto la mappa Salta nell'angolo destro della taverna. Cadi nel vuoto."
        },
        {
            "ticket_id": 103,
            "platform": "PS5",
            "category": "balancement_request",
            "text": "Nerf balestra a ripetizione La balestra spara troppo velocemente e stordisce i boss in modo permanente."
        }
    ]
    
    print("Inserimento record fittizi in corso...\n")
    table.add(dati_fittizi)

    # 3. Test 1: Nuovo feedback simile alla spada lunga
    testo_query_spada = "La spada lunga +7 fa troppi danni e rovescia il pvp. Vi prego di abbassare le sue statistiche perché non si riesce a giocare."
    print(f"TEST 1 - Cerco duplicati per:\n'{testo_query_spada}'\n")
    
    risultati_spada = find_similar_feedback(
        db=db, 
        query_text=testo_query_spada, 
        platform="UNKNOWN", 
        category="balancement_request", 
        top_k=2
    )

    SOGLIA = 0.85
    for r in risultati_spada:
        distanza = r["_distance"]
        is_dup = "SI" if distanza <= SOGLIA else "NO"
        print(f"ID Trovato: {r['ticket_id']} | Distanza: {distanza:.4f} | Duplicato sotto soglia? {is_dup}")
        print(f"Testo Originale: {r['text'][:80]}...\n")

    # 4. Test 2: Feedback su un argomento totalmente nuovo
    testo_query_armatura = "L'armatura del cavaliere oscuro pesa troppo e non fa correre."
    print(f"TEST 2 - Cerco duplicati per:\n'{testo_query_armatura}'\n")
    
    risultati_armatura = find_similar_feedback(
        db=db, 
        query_text=testo_query_armatura, 
        platform="UNKNOWN", 
        category="balancement_request", 
        top_k=2
    )

    for r in risultati_armatura:
        distanza = r["_distance"]
        is_dup = "SI" if distanza <= SOGLIA else "NO"
        print(f"ID Trovato: {r['ticket_id']} | Distanza: {distanza:.4f} | Duplicato sotto soglia? {is_dup}")
        print(f"Testo Originale: {r['text'][:80]}...\n")

    # 5. Pulizia del database
    db.drop_table("feedback_vectors")
    print("Test concluso. Tabella eliminata per ripristinare l'ambiente.")

if __name__ == "__main__":
    esegui_test_videogioco()