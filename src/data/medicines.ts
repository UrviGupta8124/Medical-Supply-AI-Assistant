export const verifiedMedicines = [
  {
    id: "m001",
    name: "Amoxicillin",
    class: "Antibiotic",
    indications: ["Bacterial infections", "Pneumonia", "Bronchitis", "Ear infections"],
    dosage: "500mg every 8 hours or 875mg every 12 hours for adults.",
    sideEffects: ["Nausea", "Vomiting", "Diarrhea", "Rash"],
    contraindications: ["Penicillin allergy"],
    defenseContext: "Standard issue in field medical kits for broad-spectrum bacterial infections. Ensure patient has no penicillin allergy before administration."
  },
  {
    id: "m002",
    name: "Ibuprofen",
    class: "NSAID",
    indications: ["Pain relief", "Fever reduction", "Inflammation"],
    dosage: "200-400mg every 4-6 hours. Max 3200mg/day.",
    sideEffects: ["Stomach pain", "Heartburn", "Bleeding risk"],
    contraindications: ["Active ulcer", "History of GI bleeding"],
    defenseContext: "Primary non-opioid analgesic for combat-related minor injuries and sprains. Take with food if possible."
  },
  {
    id: "m003",
    name: "Epinephrine (Adrenalin)",
    class: "Alpha/Beta Agonist",
    indications: ["Anaphylaxis", "Cardiac arrest", "Severe asthma"],
    dosage: "0.3mg to 0.5mg IM for anaphylaxis.",
    sideEffects: ["Palpitations", "Sweating", "Anxiety", "Tremor"],
    contraindications: ["None in life-threatening emergencies"],
    defenseContext: "Critical lifesaving medication. All personnel should carry auto-injectors in high-risk environments. Administer immediately upon signs of severe allergic reaction."
  },
  {
    id: "m004",
    name: "Morphine Sulfate",
    class: "Opioid Analgesic",
    indications: ["Severe pain"],
    dosage: "2-10mg IV initially, titrate to effect.",
    sideEffects: ["Respiratory depression", "Sedation", "Hypotension"],
    contraindications: ["Head injury", "Severe asthma", "Hypotension"],
    defenseContext: "Used for severe trauma pain. Monitor respiratory rate closely. Naloxone must be available."
  },
  {
    id: "m005",
    name: "Naloxone (Narcan)",
    class: "Opioid Antagonist",
    indications: ["Opioid overdose"],
    dosage: "0.4-2mg IV/IM/SC/IN, repeat every 2-3 minutes if necessary.",
    sideEffects: ["Precipitated withdrawal", "Tachycardia", "Agitation"],
    contraindications: ["None in emergency"],
    defenseContext: "Essential for counteracting opioid-induced respiratory depression. Carried by medics for immediate deployment."
  },
  {
    id: "m006",
    name: "Tranexamic Acid (TXA)",
    class: "Antifibrinolytic",
    indications: ["Severe hemorrhage", "Massive bleeding"],
    dosage: "1g over 10 minutes IV, followed by 1g over 8 hours.",
    sideEffects: ["Nausea", "Diarrhea", "Visual disturbances", "Thrombosis risk"],
    contraindications: ["Active intravascular clotting", "Subarachnoid hemorrhage"],
    defenseContext: "Critical for treating combat casualties with severe bleeding. Administer within 3 hours of injury for maximum effectiveness."
  },
  {
    id: "m007",
    name: "Atropine",
    class: "Anticholinergic",
    indications: ["Nerve agent poisoning", "Organophosphate poisoning", "Bradycardia"],
    dosage: "2mg IM every 5-15 minutes until secretions dry (for nerve agents).",
    sideEffects: ["Dry mouth", "Blurred vision", "Tachycardia", "Urinary retention"],
    contraindications: ["Glaucoma (relative in emergencies)"],
    defenseContext: "Component of nerve agent antidote kits (e.g., ATNAA). Administer immediately upon exposure to chemical nerve agents."
  }
];
