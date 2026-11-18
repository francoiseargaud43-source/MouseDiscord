"""Souris au même pourcentage et départage par les composants (décisions du propriétaire du 2026-11-18).

1. « Si elles ont le même taux de correspondance, l'utilisateur a le choix » : un bloc « 🟰 Au même
   pourcentage » liste, sous le match idéal, les autres souris aussi bien notées, une par coque, avec
   leur bouton d'achat.
2. « Composants à % égal » : à pourcentage égal, le meilleur capteur passe devant, puis le meilleur
   MCU, puis les meilleurs switchs (puis la fréquence), puis la moins chère. Chaque gamme garde son
   critère de tête.
"""
from __future__ import annotations

from types import SimpleNamespace

from cogs import finder_flow as flow
from utils.models import BudgetMode
from utils.selection import SENSOR_TIERS, components_index, select
from utils.slots import EQUAL_CHOICES_MAX, EQUAL_TITLE, equal_choices, result_slots


def _mouse(mouse_id, price, shell_id=None, sensor="", mcu="", switches="", polling=None):
    return SimpleNamespace(id=mouse_id, label=mouse_id, price_eur=price, shell_id=shell_id,
                           sensor=sensor, mcu=mcu, switches=switches, polling_hz=polling)


def _score(mouse, total):
    return SimpleNamespace(total=total, mouse=mouse, is_scored=True, is_pending=False, is_partial=False)


def _selection(scores, mode=BudgetMode.CUSTOM):
    return select(scores, mode, top_n=len(scores))


def test_a_pourcentage_egal_le_meilleur_capteur_passe_devant_meme_plus_cher():
    bas = _mouse("bas", 30.0, sensor="PAW3395")
    haut = _mouse("haut", 60.0, sensor="PAW3950")
    selection = _selection([_score(bas, 30), _score(haut, 30)])
    assert [s.mouse.id for s in selection.ranked] == ["haut", "bas"]


def test_a_capteur_egal_le_mcu_puis_les_switchs_puis_le_prix_departagent():
    a = _mouse("a", 50.0, sensor="PAW3950", mcu="Nordic nRF52840", switches="Optiques")
    b = _mouse("b", 70.0, sensor="PAW3950", mcu="Nordic 54L15", switches="Mécaniques")
    c = _mouse("c", 40.0, sensor="PAW3950", mcu="Nordic 54L15", switches="Optiques")
    d = _mouse("d", 35.0, sensor="PAW3950", mcu="Nordic 54L15", switches="Optiques")
    selection = _selection([_score(m, 30) for m in (a, b, c, d)])
    assert [s.mouse.id for s in selection.ranked] == ["d", "c", "b", "a"]


def test_la_main_reste_le_premier_critere():
    meilleure_forme = _mouse("forme", 80.0, sensor="PAW3395")
    meilleurs_composants = _mouse("composants", 40.0, sensor="PAW3955")
    selection = _selection([_score(meilleurs_composants, 29), _score(meilleure_forme, 30)])
    assert selection.ranked[0].mouse.id == "forme"


def test_l_economique_reste_la_moins_chere_d_abord():
    bas = _mouse("bas", 30.0, sensor="PAW3395")
    haut = _mouse("haut", 60.0, sensor="PAW3955")
    selection = _selection([_score(haut, 30), _score(bas, 30)], BudgetMode.ECONOMIQUE)
    assert selection.ranked[0].mouse.id == "bas"


def test_le_capteur_paw3950_ti_de_mchose_est_classe_comme_un_paw3950():
    assert SENSOR_TIERS["PAW3950 TI"] == SENSOR_TIERS["PAW3950"]
    assert components_index(_mouse("x", 1.0, sensor="PAW3950 TI"))[0] == 3


def test_le_bloc_liste_les_souris_au_meme_pourcentage_une_par_coque_triees_par_composants():
    ideal = _mouse("ideal", 20.0, shell_id="coque_ideal", sensor="PAW3395")
    jumelle = _mouse("jumelle", 90.0, shell_id="coque_ideal", sensor="PAW3955")      # même coque : exclue
    autre_a = _mouse("autre_a", 70.0, shell_id="coque_a", sensor="PAW3950")
    autre_a_bis = _mouse("autre_a_bis", 60.0, shell_id="coque_a", sensor="PAW3950")  # coque déjà listée
    autre_b = _mouse("autre_b", 50.0, shell_id="coque_b", sensor="PAW3955")
    moins_bien = _mouse("moins_bien", 10.0, shell_id="coque_c", sensor="PAW3955")
    scores = [_score(ideal, 32), _score(jumelle, 32), _score(autre_a, 32), _score(autre_a_bis, 32),
              _score(autre_b, 32), _score(moins_bien, 31)]
    selection = _selection(scores, BudgetMode.ECONOMIQUE)
    shown = {s.mouse.id for s in result_slots(selection) if s is not None}
    listed, others = equal_choices(selection)
    ids = [s.mouse.id for s in listed]
    assert not shown & set(ids), "une souris déjà montrée n'est jamais répétée dans le bloc"
    assert all(s.total == result_slots(selection)[0].total for s in listed)
    assert "jumelle" not in ids and not {"autre_a", "autre_a_bis"} <= set(ids)
    rangs = [components_index(s.mouse) for s in listed]
    assert rangs == sorted(rangs, reverse=True)
    assert others == 0 and len(ids) <= EQUAL_CHOICES_MAX


def test_le_bloc_est_plafonne_et_annonce_le_reste(monkeypatch):
    monkeypatch.setattr(flow, "_slot_text", lambda score, mode, partial_hint=False: score.mouse.label)
    scores = [_score(_mouse(f"m{i}", 10.0 + i, shell_id=f"coque{i}"), 30) for i in range(8)]
    selection = _selection(scores)
    listed, others = equal_choices(selection)
    shown = sum(1 for s in result_slots(selection) if s is not None)
    assert len(listed) == EQUAL_CHOICES_MAX
    assert others == 8 - shown - EQUAL_CHOICES_MAX
    texte = flow._equal_text(selection, BudgetMode.CUSTOM)
    assert texte.startswith(flow.EQUAL_INTRO)
    assert f"Et {others} autres au même pourcentage." in texte


def test_pas_de_bloc_sans_autre_souris_au_meme_pourcentage():
    scores = [_score(_mouse("a", 10.0, shell_id="a"), 30), _score(_mouse("b", 9.0, shell_id="b"), 28)]
    selection = _selection(scores)
    assert equal_choices(selection) == ((), 0)
    assert flow._equal_text(selection, BudgetMode.CUSTOM) == ""


def test_les_boutons_d_achat_passent_a_la_rangee_suivante_au_dela_de_cinq():
    souris = [_mouse(f"m{i}", 10.0) for i in range(6)]
    view = flow.ResultsView([SimpleNamespace(mouse=m) for m in souris],
                            {m.id: f"https://shop.test/{m.id}" for m in souris})
    assert [b.row for b in view.children] == [0, 0, 0, 0, 0, 1]


def test_le_vrai_resultat_montre_le_bloc_quand_des_souris_sont_a_egalite():
    """Sur le vrai catalogue : un profil où le bloc existe l'affiche sous le match idéal."""
    from utils.models import Grip
    from tests.test_flow import _trois_places

    trouve = False
    for longueur in (170.0, 180.0, 190.0):
        for largeur in (80.0, 90.0):
            session, selection, _ = _trois_places(BudgetMode.PEU_IMPORTE_PRIX, None, Grip.PALM, longueur, largeur)
            listed, _ = equal_choices(selection)
            if not listed:
                continue
            noms = [f.name for f in flow.results_embeds(session, selection)[0].fields]
            assert noms[0] == "🥇 Le match idéal" and noms[1] == EQUAL_TITLE
            trouve = True
    assert trouve, "aucun profil de contrôle n'a de souris à égalité : choisir d'autres mains"
