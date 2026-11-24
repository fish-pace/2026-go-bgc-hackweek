# 2026 GO-BGC Hackweek

**Structure**

* `contributor_folders` (optional) Each contributor can make a folder here and 
push their work here during the week. This will allow everyone to see each others work but prevent any merge conflicts.
* `final_notebooks` When the team develops shared final notebooks, they 
can be shared here. Make sure to communicate so that you limit merge conflicts.
* `scripts` Shared scripts or functions can be added here.
* `data` Shared dataset can be shared here. Note, do not put large datasets on GitHub. Speak to the organizers if you 
need to share large datasets. 

## CHLA-Z

**Ideas**

* Does the 3D CHLA estimation work with Sentinal-3 bands?
    - Rerun the BRT with fewer spectral bands
* What improves estimation? Does including other Argo variables improve?
    - For global prediction would need to use variables that we have globally. Temp & O2 from GOBAI?
* Does closer spatially help? PACE L2 (1k) versus L3 (4km)
* Try other ML approaches with the training dataset
* Test classic surf CHLA to integrated CHLA and DSL (deep scattering layer)
* Look for deeper peaks in Argo profiles? Are there any?
* Look for relationships with MLD (mixed layer depth)
* Look for interesting areas with where CHLA 3D patterns might be of interest. See https://github.com/fish-pace/chla-z/blob/main/notebooks/examples.ipynb
  
## Collaborators

| Name | ORCID | Affiliation |
|---|---|---|
| Elizabeth Eli Holmes | [0000-0001-9128-8393](https://orcid.org/0000-0001-9128-8393) | Northwest Fisheries Science Center, NOAA Fisheries; School of Aquatic and Fishery Sciences, University of Washington (affiliate faculty) |
| Andrea Albright | [0000-0003-2670-1625](https://orcid.org/0000-0003-2670-1625) | Michigan Tech Research Institute, Michigan Technological University |
| Jodi Brewster | | Rosenstiel School of Marine, Atmospheric, and Earth Science, University of Miami |
| Peter Mastnak | | Department of Oceans, Stanford University |
| Charlie Turner | | University of California, Davis |
| Nabir Mamnun | [0000-0003-3032-114X](https://orcid.org/0000-0003-3032-114X) | Department of Physics, Imperial College London |
| Haipeng Zhao | [0000-0001-9142-1684](https://orcid.org/0000-0001-9142-1684) | School of Earth and Atmospheric Sciences, Georgia Institute of Technology |
| Kai Yang | [0000-0002-1074-3081](https://orcid.org/0000-0002-1074-3081) | State Key Laboratory of Marine Environmental Science, Xiamen University |

## Results

## References

* https://fish-pace.github.io/chla-z/
* https://agupubs.onlinelibrary.wiley.com/doi/10.1002/2014JC010355
* https://data.marine.copernicus.eu/product/MULTIOBS_GLO_BIO_BGC_3D_REP_015_010/description
* 

