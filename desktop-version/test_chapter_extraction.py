import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup

import chapters
import main


class ChapterExtractionTests(unittest.TestCase):
    def test_ui_exposes_only_supported_actions_and_labels_chapter_title(self):
        web_dir = Path(__file__).with_name("web")
        document = BeautifulSoup(
            (web_dir / "index.html").read_text(encoding="utf-8"),
            "html.parser",
        )
        actions = [
            button.get("data-value")
            for button in document.select(".tab-button")
        ]
        script = (web_dir / "script.js").read_text(encoding="utf-8")

        self.assertEqual(actions, ["epub", "txt", "unificar"])
        epub_tab = document.select_one('.tab-button[data-value="epub"]')
        self.assertEqual(epub_tab.get("aria-pressed"), "true")
        self.assertIn("alterarModo('epub')", script)
        self.assertIn("Título do capítulo", script)
        examples = document.select("#sourceHelp li")
        self.assertEqual(len(examples), 2)
        self.assertIn(
            "https://centralnovel.com/shadow-slave-capitulo-1/",
            examples[0].get_text(" ", strip=True),
        )
        self.assertIn(
            "https://freewebnovel.com/novel/captured-by-the-cold-detective-bl/chapter-1",
            examples[1].get_text(" ", strip=True),
        )

    def test_builds_site_specific_chapter_urls(self):
        self.assertEqual(
            chapters.montar_url_capitulo(
                "https://centralnovel.com/shadow-slave-capitulo-", 12
            ),
            "https://centralnovel.com/shadow-slave-capitulo-12",
        )
        self.assertEqual(
            chapters.montar_url_capitulo(
                "https://centralnovel.com/shadow-slave-capitulo-1/", 12
            ),
            "https://centralnovel.com/shadow-slave-capitulo-12/",
        )
        self.assertEqual(
            chapters.montar_url_capitulo(
                "https://centralnovel.com/shadow-slave-capitulo-1/?ref=test", 12
            ),
            "https://centralnovel.com/shadow-slave-capitulo-12/?ref=test",
        )
        self.assertEqual(
            chapters.montar_url_capitulo(
                "https://freewebnovel.com/novel/example-title/chapter-1", 12
            ),
            "https://freewebnovel.com/novel/example-title/chapter-12",
        )

    def test_rejects_example_slug_and_non_chapter_formats(self):
        with self.assertRaisesRegex(ValueError, "slug de exemplo"):
            chapters.validar_url_fonte(
                "https://freewebnovel.com/novel/nome-da-obra/chapter-1"
            )

        with tempfile.TemporaryDirectory() as output_dir:
            with patch.multiple(
                main,
                MAX_CONCURRENT=10,
                TIMEOUT=20,
                MIN_DELAY=0,
                MAX_DELAY=0,
            ):
                response = main.iniciar_download_desktop(
                    "https://centralnovel.com/shadow-slave-capitulo-",
                    1,
                    1,
                    "zip",
                    "chapters",
                    {"maxConcurrent": 3, "timeout": 60, "minDelay": 0, "maxDelay": 0},
                    output_dir,
                )
            self.assertFalse(response["ok"])
            self.assertIn("Formato de saída não suportado", response["msg"])
            self.assertEqual(os.listdir(output_dir), [])

    def test_extracts_central_novel_chapter_and_uses_shared_output_format(self):
        html = """
        <div class="epheader">
          <h1 class="entry-title" itemprop="headline">Shadow  Slave – Capítulo&nbsp; 1</h1>
          <div class="cat-series">O Pesadelo Começa</div>
        </div>
        <div class="epcontent entry-content">
          <p>O primeiro parágrafo.</p>
          <p>O segundo <em>parágrafo</em>.</p>
        </div>
        """

        chapter = chapters.extrair_capitulo(
            BeautifulSoup(html, "html.parser"),
            "https://centralnovel.com/shadow-slave-capitulo-",
            1,
        )

        self.assertEqual(chapter.numero, "1")
        self.assertEqual(chapter.nome_capitulo, "O Pesadelo Começa")
        self.assertEqual(chapter.obra, "Shadow Slave")
        self.assertEqual(chapter.titulo, "Capítulo 1: O Pesadelo Começa")
        self.assertEqual(
            chapters.formatar_nome_arquivo_capitulo(chapter),
            "Capítulo 00001 - O Pesadelo Começa - Shadow Slave.txt",
        )
        self.assertEqual(
            chapter.paragrafos,
            ("O primeiro parágrafo.", "O segundo parágrafo."),
        )
        self.assertTrue(
            chapters.formatar_conteudo_txt(chapter).startswith(
                "Capítulo 1: O Pesadelo Começa\nShadow Slave\n\n"
            )
        )

    def test_extracts_freewebnovel_chapter_into_the_same_data_shape(self):
        html = """
        <h1 class="tit"><a>Captured By The Cold Detective (BL)</a></h1>
        <span class="chapter">Chapter 1: Missing Neighbor</span>
        <div id="article">
          <h2>Chapter 1: Missing Neighbor</h2>
          <p>First paragraph.</p>
          <p>Second paragraph.</p>
        </div>
        """

        chapter = chapters.extrair_capitulo(
            BeautifulSoup(html, "html.parser"),
            "https://freewebnovel.com/novel/captured-by-the-cold-detective-bl/chapter-1",
            1,
        )

        self.assertEqual(chapter.numero, "1")
        self.assertEqual(chapter.nome_capitulo, "Missing Neighbor")
        self.assertEqual(chapter.obra, "Captured By The Cold Detective (BL)")
        self.assertEqual(chapter.titulo, "Chapter 1: Missing Neighbor")
        self.assertEqual(
            chapters.formatar_nome_arquivo_capitulo(chapter),
            "Capítulo 00001 - Missing Neighbor - Captured By The Cold Detective (BL).txt",
        )
        self.assertEqual(chapter.paragrafos, ("First paragraph.", "Second paragraph."))
        self.assertTrue(
            chapters.formatar_conteudo_txt(chapter).startswith(
                "Chapter 1: Missing Neighbor\nCaptured By The Cold Detective (BL)\n\n"
            )
        )

    @unittest.skipIf(main.epub is None, "EbookLib is not installed")
    def test_epub_uses_normalized_chapter_title_and_paragraphs(self):
        chapter = chapters.Capitulo(
            indice=1,
            numero="1",
            titulo="Capítulo 1: O Pesadelo Começa",
            nome_capitulo="O Pesadelo Começa",
            obra="Shadow Slave",
            paragrafos=("Primeiro parágrafo.", "Segundo parágrafo."),
        )

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = os.path.join(output_dir, "shadow-slave.epub")
            main.gerar_arquivo_epub(
                [chapter],
                output_path,
                "https://centralnovel.com/shadow-slave-capitulo-",
            )

            with zipfile.ZipFile(output_path) as epub_file:
                chapter_path = next(
                    name
                    for name in epub_file.namelist()
                    if name.endswith("chapter_00001.xhtml")
                )
                chapter_html = epub_file.read(chapter_path).decode("utf-8")

        chapter_text = BeautifulSoup(chapter_html, "html.parser").get_text(" ", strip=True)
        self.assertIn("Capítulo 1: O Pesadelo Começa", chapter_text)
        self.assertIn("Primeiro parágrafo.", chapter_text)
        self.assertIn("Segundo parágrafo.", chapter_text)

    def test_txt_files_and_progress_log_include_chapter_titles_for_both_sites(self):
        cases = (
            (
                """
                <h1 class="entry-title">Shadow Slave – Capítulo&nbsp; 1</h1>
                <div class="cat-series">O Pesadelo Começa</div>
                <div class="epcontent entry-content"><p>Primeiro parágrafo.</p></div>
                """,
                "https://centralnovel.com/shadow-slave-capitulo-",
                "Capítulo 00001 - O Pesadelo Começa - Shadow Slave.txt",
                "Capítulo 1: O Pesadelo Começa",
                "Primeiro parágrafo.",
            ),
            (
                """
                <h1 class="tit"><a>Captured By The Cold Detective (BL)</a></h1>
                <span class="chapter">Chapter 1: Missing Neighbor</span>
                <div id="article"><p>First paragraph.</p></div>
                """,
                "https://freewebnovel.com/novel/captured-by-the-cold-detective-bl/chapter-1",
                "Capítulo 00001 - Missing Neighbor - Captured By The Cold Detective (BL).txt",
                "Chapter 1: Missing Neighbor",
                "First paragraph.",
            ),
        )

        class Callbacks:
            def __init__(self):
                self.progress_calls = []

            def receberProgresso(self, *args):
                self.progress_calls.append(args)
                return lambda: None

            def registrarErro(self, *args):
                return lambda: None

        for html, url_base, expected_name, expected_title, expected_paragraph in cases:
            with self.subTest(url_base=url_base), tempfile.TemporaryDirectory() as output_dir:
                response = SimpleNamespace(status_code=200, text=html)
                state = {"atual": 0, "capitulos_epub": []}
                callbacks = Callbacks()
                with patch.object(main, "baixar_pagina_desktop", return_value=response):
                    with patch.object(main, "eel", callbacks):
                        main.baixar_capitulo_individual(
                            url_base, 1, output_dir, 1, state, "txt"
                        )

                        txt_path = os.path.join(output_dir, expected_name)
                        with open(txt_path, encoding="utf-8") as chapter_file:
                            txt_content = chapter_file.read()
                        self.assertTrue(txt_content.startswith(expected_title))
                        self.assertIn(expected_paragraph, txt_content)
                self.assertEqual(callbacks.progress_calls, [(expected_title, 1, 1, 1)])


if __name__ == "__main__":
    unittest.main()
