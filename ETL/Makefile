# extract-descriptors / annotate-opt / update-silver-posts only process the posts
# of one public.dataset id: conf/config.yaml's dataset_id unless overridden, e.g.
# `make annotate-opt DATASET_ID=2`. `DATASET_ID=null` processes every post.
DATASET_ID ?=
DATASET_ARG = $(if $(DATASET_ID),dataset_id=$(DATASET_ID),)

.PHONY: install clean reinstall bronze silver extract-descriptors gold annotate-opt update-silver-posts create-vocab load-eval

install:
	bash bin/set_env.sh

clean:
	conda env remove -y -n etl

reinstall: clean install

bronze:
	PYTHONPATH=.. python main_bronze.py

silver:
	PYTHONPATH=.. python main_silver.py

extract-descriptors:
	PYTHONPATH=.. python main_extract_formula_descriptors.py $(DATASET_ARG)

gold:
	PYTHONPATH=.. python main_gold.py

annotate-opt:
	PYTHONPATH=.. python main_annotate_opt_formulas.py $(DATASET_ARG)

update-silver-posts:
	PYTHONPATH=.. python main_update_silver_posts.py $(DATASET_ARG)

create-vocab:
	PYTHONPATH=.. python main_create_vocab.py

load-eval:
	PYTHONPATH=.. python main_load_arqmath_eval.py
