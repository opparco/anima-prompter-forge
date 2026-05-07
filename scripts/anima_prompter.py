import html
import json
import gradio as gr

from anima_prompter import DEFAULT_NEGATIVE, LMStudioError, LMStudioPrompter
from modules import script_callbacks, scripts, shared
from modules.ui_components import InputAccordion


class AnimaPrompterScript(scripts.Script):
    sorting_priority = -100

    def __init__(self):
        super().__init__()
        self.prompt_component = None
        self.prompt_elem_id = None
        self.neg_prompt_component = None

    def title(self):
        return "Anima Prompter"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def after_component(self, component, **kwargs):
        elem_id = getattr(component, "elem_id", None)
        expected_prompt = "img2img_prompt" if self.is_img2img else "txt2img_prompt"
        expected_neg = "img2img_neg_prompt" if self.is_img2img else "txt2img_neg_prompt"

        if elem_id == expected_prompt:
            self.prompt_component = component
            self.prompt_elem_id = elem_id
        elif elem_id == expected_neg:
            self.neg_prompt_component = component

    def ui(self, is_img2img):
        with InputAccordion(False, label="Anima Prompter", elem_id=self.elem_id("panel")):
            concept = gr.Textbox(
                label="Concept",
                lines=3,
                placeholder="Describe the scene or theme to expand into an Anima prompt.",
                elem_id=self.elem_id("concept"),
            )
            reference_image = gr.File(
                label="Reference Image",
                file_count="single",
                type="binary",
                elem_id=self.elem_id("reference_image"),
            )
            generate_button = gr.Button("Generate Prompt", variant="secondary", elem_id=self.elem_id("generate"))
            generated_prompt = gr.Textbox(
                label="Generated Prompt",
                lines=6,
                interactive=False,
                elem_id=self.elem_id("generated_prompt"),
            )
            status = gr.HTML(value="", elem_id=self.elem_id("status"))
            raw_json = gr.Textbox(
                label="Raw LM JSON",
                lines=8,
                interactive=False,
                elem_id=self.elem_id("raw_json"),
            )
            prompt_output = self.prompt_component
            if prompt_output is None:
                prompt_output = gr.Textbox(visible=False, elem_id=self.elem_id("prompt_shadow"))

            neg_prompt_output = self.neg_prompt_component
            if neg_prompt_output is None:
                neg_prompt_output = gr.Textbox(visible=False, elem_id=self.elem_id("neg_prompt_shadow"))

        generate_button.click(
            fn=self._generate_prompt,
            inputs=[concept, reference_image, neg_prompt_output],
            outputs=[prompt_output, neg_prompt_output, generated_prompt, status, raw_json],
        )

        return [concept, reference_image, generated_prompt, status, raw_json]

    def _generate_prompt(self, concept: str, reference_image: bytes | None, current_neg_prompt: str | None):
        concept = (concept or "").strip()
        if not concept:
            message = self._status("Enter a concept before generating.", error=True)
            return gr.update(), gr.update(), gr.update(value=""), message, gr.update(value="")

        prompter = LMStudioPrompter(
            base_url=shared.opts.data.get("anima_prompter_lmstudio_url", "http://192.168.11.21:1234"),
            timeout=float(shared.opts.data.get("anima_prompter_timeout", 60.0)),
        )

        try:
            prompt, raw = prompter.generate(
                concept=concept,
                ref_image_bytes=reference_image,
                ref_image_name="reference.png" if reference_image is not None else None,
            )
        except LMStudioError as error:
            message = self._status(str(error), error=True)
            return gr.update(), gr.update(), gr.update(value=""), message, gr.update(value="")
        except Exception as error:
            message = self._status(f"Unexpected error: {error}", error=True)
            return gr.update(), gr.update(), gr.update(value=""), message, gr.update(value="")

        prompt_text = prompt.build_string()

        if not (current_neg_prompt or "").strip():
            neg_update = gr.update(value=prompt.build_negative_string())
        else:
            neg_update = gr.update()

        if self.prompt_component is None:
            message = self._status("Generated prompt preview only. Target prompt textbox was not found.", error=True)
        else:
            message = self._status(f"Applied generated prompt to `{self.prompt_elem_id}`.", error=False)
        raw_text = json.dumps(raw, indent=2, ensure_ascii=False)
        return (
            gr.update(value=prompt_text),
            neg_update,
            gr.update(value=prompt_text),
            message,
            gr.update(value=raw_text),
        )

    @staticmethod
    def _status(message: str, *, error: bool) -> str:
        color = "#b42318" if error else "#027a48"
        return f"<div style='color:{color}'>{html.escape(message)}</div>"


def on_ui_settings():
    section = ("Anima Prompter", "Anima Prompter")
    shared.opts.add_option(
        "anima_prompter_lmstudio_url",
        shared.OptionInfo(
            default="http://192.168.11.21:1234",
            label="LM Studio base URL",
            component=gr.Textbox,
            section=section,
        ),
    )
    shared.opts.add_option(
        "anima_prompter_timeout",
        shared.OptionInfo(
            default=60.0,
            label="Request timeout (seconds)",
            component=gr.Slider,
            component_args={"minimum": 5.0, "maximum": 300.0, "step": 1.0},
            section=section,
        ),
    )


script_callbacks.on_ui_settings(on_ui_settings)
