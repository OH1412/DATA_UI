import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { DataGuide } from './components/DataGuide';
import { AssetActions, RecordingReview, ReviewedEpisodes } from './components/WorkspaceInteractions';
import './styles/global.css';
import './styles/details.css';
import './styles/rollback.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /><DataGuide /><RecordingReview /><ReviewedEpisodes /><AssetActions /></React.StrictMode>);
