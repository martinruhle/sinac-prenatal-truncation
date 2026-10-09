-- FACT_RELATIONSHIP: the mother and the newborn of each loaded record, linked in both directions,
-- as the CDM asks of every relationship (D-104, docs/omop_mapping.md §FACT_RELATIONSHIP). A row
-- reads "fact 1 is <relationship> of fact 2", and both facts are PERSONs:
--   - the mother is the Mother of the newborn;
--   - the newborn is the Child of the mother.
-- The cohort SQL tells the mothers apart from the newborns through the first row (D-106).
WITH concepts AS (
    SELECT
        max(concept_id) FILTER (WHERE concept_key = 'person_table') AS person,
        max(concept_id) FILTER (WHERE concept_key = 'mother') AS mother,
        max(concept_id) FILTER (WHERE concept_key = 'child') AS child
    FROM @results_schema.concept_sets
)

INSERT INTO @cdm_schema.fact_relationship (
    domain_concept_id_1,
    fact_id_1,
    domain_concept_id_2,
    fact_id_2,
    relationship_concept_id
)
SELECT
    c.person,
    l.fact_id_1::integer,
    c.person,
    l.fact_id_2::integer,
    l.relationship_concept_id
FROM pg_temp.records AS r
CROSS JOIN concepts AS c
CROSS JOIN LATERAL (
    VALUES
    (r.person_id, r.newborn_person_id, c.mother),
    (r.newborn_person_id, r.person_id, c.child)
) AS l (fact_id_1, fact_id_2, relationship_concept_id)
WHERE r.loaded;
