.PHONY: install clean reinstall bronze silver extract-descriptors gold annotate-opt update-silver-posts

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
	PYTHONPATH=.. python main_extract_formula_descriptors.py

gold:
	PYTHONPATH=.. python main_gold.py

annotate-opt:
	PYTHONPATH=.. python main_annotate_opt_formulas.py

update-silver-posts:
	PYTHONPATH=.. python main_update_silver_posts.py
