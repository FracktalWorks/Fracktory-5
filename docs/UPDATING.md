# Updating AddiSlice

This guide covers the process of updating AddiSlice to incorporate changes from the latest Ultimaker Cura releases.

## Updating to Latest Ultimaker Cura Version

Follow these steps to update AddiSlice with the latest Ultimaker Cura version:

1. **Navigate to Ultimaker Cura repository**: Go to the [Ultimaker Cura repository](https://github.com/Ultimaker/Cura) and select the release you want to update to:

![alt text](cura_repo_version.png)

2. **Open the associated commit**: Click on the commit associated with the release:

![alt text](cura_release_commit.png)

3. **Note the branch and tag**: Record the branch and tag associated with the commit (e.g., branch: `5.9`, tag: `5.9.1-RC3`):

![alt text](branch-tag.png)

4. **Select upstream branch**: In GitHub Desktop, select the upstream branch from step 3 (e.g., `5.9` or `upstream/5.9`). If you don't see the branch, click "Fetch" to get the latest upstream changes:

![alt text](open_upstream_branch.png)

5. **Create branch from commit**: Navigate to the commit history of that branch, find the commit with the tag from step 3, right-click and select "Create branch from commit":

![alt text](navigate_history.png)

![alt text](create_branch_from_commit.png)

6. **Create new AddiSlice branch**: Create a new branch for AddiSlice with the new version number (e.g., "AddiSlice-5.6.0"):

![alt text](create_branch.png)

7. **Switch and publish**: In GitHub Desktop, switch to the new branch and publish it to the cloud:

![alt text](switch_branch.png)

![alt text](publish_branch.png)

8. **Clean resources folder**: Delete third-party printer profiles that will create merge conflicts. Remove profiles in `intents`, `quality`, `definitions`, and `variants` folders within `resources`. **Be careful not to delete core files** like `fdmprinter` and `fdmextruder`:

This is what it might look like before deleting:
![alt text](resources_old.png)

After deleting only the core resource files are left:
![alt text](resources_new.png)

9. **Merge previous AddiSlice version**: Merge the previous AddiSlice 5 release branch into the current branch. Use squash and merge for a cleaner commit history: 

![alt text](merge.png)

![alt text](previous_branch.png)

10. **Resolve conflicts**: Use GitHub Desktop and VS Code source control to resolve any merge conflicts:

![alt text](resolve_github.png)

![alt text](resolve_vscode.png)

11. **Update conandata.yaml**: Update with the latest versioning from the upstream Cura repository. Comment out requirements to prevent the installer from overriding them:

![alt text](conan.png)

12. **Update latest.json**: Copy version information from `conandata.yaml` to `latest.json` for version checking:

![alt text](latest_json.png)

13. **Update GitHub Actions**: Update the `cura-installer-windows.yml` workflow with the latest version numbers for AddiSlice and CuraEngine. You may need to update the build environment if GitHub Actions, Python version, or Conan have been updated upstream: 

![alt text](application_version.png)

14. **Set default branch**: Change the default branch on GitHub to the new version. See [GitHub's guide](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/changing-the-default-branch):

![alt text](change_default.png)

15. **Update CuraEngine**: Follow the same process for CuraEngine and set its default branch to the latest version: 

![alt text](cura_engine_upstream_branch.png)

![alt text](cura_engine_create_branch.png)

![alt text](name_engine.png)

![alt text](engine_publish_branch.png)

![alt text](engine_merge.png)

![alt text](previous_engine.png)

![alt text](default_engine.png)

16. **Rebuild**: Follow the build instructions to compile AddiSlice and CuraEngine again. The build environment may need updates - reference the [Running Cura from Source guide](https://github.com/Ultimaker/Cura/wiki/Running-Cura-from-Source).

17. **Update GitHub Actions**: Ensure GitHub Actions work properly by referencing the [Cura Windows Installer Workflow](https://github.com/Ultimaker/cura-workflows/blob/main/.github/workflows/cura-installer-windows.yml) and updating `\AddiSlice\.github\workflows\cura-installer-windows.yml` accordingly.

## Summary

This process ensures that AddiSlice stays up-to-date with the latest Ultimaker Cura improvements while maintaining AddiPrint-specific customizations. After completing these steps, you'll have a new AddiSlice version that incorporates the latest upstream changes.

For questions about this process or if you encounter issues, please refer to the main [README](README.md) or open an issue in the repository.