import { Element } from '@wdio/sync';
import { makeLauncher } from '../rmf-launcher';
import { login, overwriteClick } from './utils';

describe('door request', () => {
  let doorItem: Element;
  const launcher = makeLauncher();

  before(async () => await launcher.launch());
  after(async () => await launcher.kill());

  before(() => overwriteClick());
  before(() => browser.url('/'));

  before(login);

  before(() => {
    $('[data-component=MainMenu] [data-item=Doors]').click();
    doorItem = $('[data-component=DoorItem]');
    doorItem.click();
  });

  it('clicking on open button opens the door', () => {
    expect(doorItem).toHaveAttr('data-state', 'CLOSED');

    doorItem.$('button=Open').click();

    expect(doorItem).toHaveAttr('data-state', 'OPEN');
  });

  it('clicking on close button closes the door', () => {
    expect(doorItem).toHaveAttr('data-state', 'OPEN');

    doorItem.$('button=Close').click();

    expect(doorItem).toHaveAttr('data-state', 'CLOSED');
  });
});
