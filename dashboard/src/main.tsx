import { BrowserRouter } from 'react-router-dom';
import { createRoot } from 'react-dom/client';
import './index.css';
import RouterApp from './App';

createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <RouterApp />
  </BrowserRouter>,
);
