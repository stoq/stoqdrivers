PACKAGE=stoqdrivers
TEST_PACKAGES=$(PACKAGE) tests
WEBDOC_DIR=/mondo/htdocs/stoq.com.br/doc/devel
# FIXME: This probably should be on utils.mk
TESTS_RUNNER=python3 -m nose --nocapture --nologcapture --verbose --detailed-errors

stoqdrivers.pickle:
	pydoctor --project-name="Stoqdrivers" \
		 --add-package=stoqdrivers \
		 -o stoqdrivers.pickle stoqdrivers

apidocs: stoqdrivers.pickle
	pydoctor --project-name="Stoqdrivers" \
		 --make-html \
		 -p stoqdrivers.pickle

web: apidocs
	cp -r apidocs $(WEBDOC_DIR)/stoqdrivers-tmp
	rm -fr $(WEBDOC_DIR)/stoqdrivers
	mv $(WEBDOC_DIR)/stoqdrivers-tmp $(WEBDOC_DIR)/stoqdrivers
	cp stoqdrivers.pickle $(WEBDOC_DIR)/stoqdrivers

lint:
	flake8 .

check: lint
	@rm -f .noseids
	$(TESTS_RUNNER) --failed $(TEST_PACKAGES)

check-failed:
	$(TESTS_RUNNER) --failed $(TEST_PACKAGES)

coverage: lint
	$(TESTS_RUNNER) --with-coverage --with-xunit \
	                --cover-package=$(PACKAGE) --cover-erase $(TEST_PACKAGES)

include utils/utils.mk
.PHONY: clean stoqdrivers.pickle
